"""LlamaCPP inference server manager.

Manages llama-server processes required by the Aria web UI:
  - Chat server (port 7070): launched via the bundled ``run-model`` script
  - Embeddings server (port 7072): launched via ``run-model --embedding``
  - Rerank server (port 7073): launched via ``run-model --reranking``

The VL (vision/language) server is NOT started automatically. It starts
on-demand when the user invokes a vision command (e.g., ``aria vision pdf``).

The ``run-model`` script handles GPU detection, KV cache tuning, flash attention,
and dual-GPU configuration automatically for all servers. For embeddings, it uses
the ``--embedding`` flag for deterministic output and ``--parallel`` for batch processing.
For reranking, it uses the ``--reranking`` flag similarly.

Example:
    ```python
    from aria.server.llama import LlamaCppServerManager

    manager = LlamaCppServerManager(context_size=8192)
    manager.start_all()   # starts chat + embeddings + rerank, waits for /health
    # ... run Chainlit ...
    manager.stop_all()    # graceful shutdown
    ```
"""

import os
import subprocess
import time
from pathlib import Path
from typing import Optional
from urllib.error import URLError
from urllib.request import urlopen

from loguru import logger

from aria.config.api import LlamaCpp as LlamaCppConfig
from aria.config.folders import Data as DataConfig
from aria.server.process_utils import (
    clear_state,
    is_process_running,
    load_state,
    save_state,
    stop_process,
)


class LlamaCppServerManager:
    """Manages the llama-server processes for chat, VL, embeddings, and rerank.

    All servers are launched via the bundled ``data/bin/run-model`` script
    which handles GPU detection, KV cache tuning, and flash attention.

    The embeddings server uses ``--embedding`` flag for deterministic output
    and ``--parallel`` for batch processing.
    The rerank server uses ``--reranking`` flag for deterministic reranking
    and ``--parallel`` for batch processing.

    Process state is persisted to ``data/llama_servers.json`` so the manager
    can track servers started by other processes (e.g. CLI to GUI).

    Context sizes are read from LlamaCppConfig:
        - chat_context_size: Context for chat server
        - vl_context_size: Context for VL server
        - embeddings_context_size: Context for embeddings server
        - rerank_context_size: Context for rerank server

    Args:
        gpu_layers: Number of GPU layers (default 999 = all layers on GPU).
        host: Host address for all servers.

    Example:
        ```python
        manager = LlamaCppServerManager()
        manager.start_all()
        # ... run Chainlit ...
        manager.stop_all()
        ```
    """

    PID_FILE = DataConfig.path / "llama_servers.json"
    RUN_MODEL_SCRIPT = DataConfig.path / "bin" / "run-model"
    EMBEDDINGS_PARALLEL = 1
    HEALTH_POLL_INTERVAL = 0.5
    HEALTH_TIMEOUT = 120  # seconds

    def __init__(
        self,
        gpu_layers: int = 999,
        host: str = "0.0.0.0",
    ):
        self._gpu_layers = gpu_layers
        self._host = host
        self._pids: dict[str, int] = self._load_valid_pids()

    def _load_valid_pids(self) -> dict[str, int]:
        """Load PIDs from state file, filtering to only running processes."""
        state = load_state(self.PID_FILE)
        return {
            role: pid
            for role, pid in state.items()
            if isinstance(pid, int) and is_process_running(pid)
        }

    def _save_pids(self) -> None:
        """Save current PIDs to state file."""
        save_state(self.PID_FILE, self._pids)

    def _clear_pids(self) -> None:
        """Clear state file and reset in-memory PIDs."""
        self._pids.clear()
        clear_state(self.PID_FILE)

    def _resolve_model_path(self, role: str, filename: str) -> Path:
        """Resolve model path by exact filename, raising RuntimeError if not found."""
        from aria.scripts.gguf import get_model_path

        if not filename:
            raise RuntimeError(
                f"Model filename for role '{role}' is not configured. "
                f"Set the corresponding env var in your .env file."
            )

        models_dir = LlamaCppConfig.models_path
        model_path = get_model_path(filename, models_dir)

        if model_path is None:
            raise RuntimeError(
                f"Model file '{filename}' for role '{role}' "
                f"not found in {models_dir}. Run: aria models download --model {role}"
            )

        return model_path

    def _build_run_model_cmd(
        self,
        model_path: Path,
        context_size: int,
        port: int,
        role: str,
        mmproj_path: Optional[Path] = None,
        embedding_mode: bool = False,
        chat_template_file: Optional[Path] = None,
        reranking_mode: bool = False,
    ) -> list[str]:
        """Build command to launch a server via run-model script.

        Args:
            model_path: Path to the GGUF model file.
            context_size: Context size in tokens.
            port: Port to run the server on.
            role: Server role name (chat/vl/embeddings/rerank), used for log file naming.
            mmproj_path: Optional path to mmproj file for vision models.
            embedding_mode: If True, run in embedding mode (deterministic).
            chat_template_file: Optional path to a Jinja2 chat template
                file.  Passed as ``--chat-template-file`` to
                llama-server (chat mode only).
            reranking_mode: If True, run in reranking mode (deterministic).

        Raises:
            ValueError: If both embedding_mode and reranking_mode are True.
        """
        if embedding_mode and reranking_mode:
            raise ValueError(
                "embedding_mode and reranking_mode are mutually exclusive"
            )

        from aria.config.folders import Debug as DebugConfig

        log_file = DebugConfig.logs_path.parent / f"llama-{role}.log"

        cmd = [
            str(self.RUN_MODEL_SCRIPT),
            str(model_path),
            str(context_size),
            "--port",
            str(port),
            "--log-file",
            str(log_file),
        ]

        if embedding_mode:
            cmd.append("--embedding")
            cmd.extend(["--parallel", str(self.EMBEDDINGS_PARALLEL)])

        if reranking_mode:
            cmd.append("--reranking")
            cmd.extend(["--parallel", str(self.EMBEDDINGS_PARALLEL)])

        if mmproj_path:
            cmd.extend(["--mmproj", str(mmproj_path)])

        # Chat template is only valid for chat mode — never for
        # embedding or reranking servers which have no chat/tool-call handling.
        if chat_template_file and not embedding_mode and not reranking_mode:
            cmd.extend(
                [
                    "--chat-template-file",
                    str(chat_template_file),
                ]
            )

        return cmd

    def _get_env_for_run_model(self) -> dict:
        """Build environment for the run-model script.

        Sets ``LLAMA_SERVER_PATH`` to the absolute path of the llama-server
        binary and prepends the binary directory to ``LD_LIBRARY_PATH`` (Linux)
        or ``DYLD_LIBRARY_PATH`` (macOS) so that the shared libraries bundled
        alongside the binary (``libllama.so``, ``libggml*.so``, etc.) are found
        at runtime.
        """
        import platform

        env = os.environ.copy()
        bin_path = LlamaCppConfig.bin_path
        env["LLAMA_SERVER_PATH"] = str(bin_path / "llama-server")

        # Prepend the bin directory to library path so the bundled
        # shared libraries are resolved when llama-server is executed.
        # Linux uses LD_LIBRARY_PATH, macOS uses DYLD_LIBRARY_PATH.
        if platform.system() == "Darwin":
            existing = env.get("DYLD_LIBRARY_PATH", "")
            env["DYLD_LIBRARY_PATH"] = (
                f"{bin_path}:{existing}" if existing else str(bin_path)
            )
        else:
            existing = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = (
                f"{bin_path}:{existing}" if existing else str(bin_path)
            )

        # KV cache location: when kv_cache_offload is True, pass
        # --no-kv-offload to move KV cache from GPU VRAM to system RAM
        # (slower but saves VRAM). Empty string = keep KV cache on GPU.
        env["NO_KV_OFFLOAD"] = (
            "--no-kv-offload" if LlamaCppConfig.kv_cache_offload else ""
        )

        # Always clear CHAT_TEMPLATE_FILE from the inherited environment
        # so the run-model script doesn't apply it to VL or embedding
        # servers.  The chat server receives it as an explicit CLI
        # argument from _build_run_model_cmd() instead.
        env.pop("CHAT_TEMPLATE_FILE", None)

        # Force context: bypass the script's VRAM-based safety cap so
        # that CHAT_CONTEXT_SIZE / VL_CONTEXT_SIZE / EMBEDDINGS_CONTEXT_SIZE
        # from .env are honored exactly as configured.
        env["FORCE_CONTEXT"] = "1" if LlamaCppConfig.force_context else "0"

        return env

    def _wait_for_ready(
        self, host: str, port: int, timeout: Optional[float] = None
    ) -> bool:
        """Poll ``/health`` until the server returns HTTP 200 or timeout.

        Args:
            host: Server host.
            port: Server port.
            timeout: Maximum seconds to wait (default: ``HEALTH_TIMEOUT``).

        Returns:
            True if the server became ready, False if timed out.
        """
        if timeout is None:
            timeout = self.HEALTH_TIMEOUT

        url = f"http://{host}:{port}/health"
        deadline = time.time() + timeout

        while time.time() < deadline:
            try:
                with urlopen(url, timeout=2) as resp:
                    if resp.status == 200:
                        return True
            except (URLError, OSError):
                pass
            time.sleep(self.HEALTH_POLL_INTERVAL)

        return False

    def start_all(self) -> None:
        """Start chat, embeddings, and rerank llama-server processes.

        The VL (vision/language) server is NOT started automatically.
        It starts on-demand when the user invokes a vision command
        (e.g., ``aria vision pdf`` or ``aria vision image``).

        The rerank server is only started if a rerank model is configured
        (i.e., ``RERANK_MODEL_FILE`` is set in the environment).

        Raises:
            RuntimeError: If any server fails to start or become ready.
        """
        from aria.config.models import Chat, Embeddings, Rerank

        # Resolve model paths by filename
        chat_path = self._resolve_model_path("chat", Chat.filename)
        emb_path = self._resolve_model_path("embeddings", Embeddings.filename)

        # Chat template file (only used by the chat server)
        chat_tpl = LlamaCppConfig.chat_template_file

        servers = [
            (
                "chat",
                chat_path,
                Chat.get_port(),
                LlamaCppConfig.chat_context_size,
                False,  # not embedding mode
                None,  # no mmproj for chat
                chat_tpl,  # chat template
                False,  # not reranking mode
            ),
            (
                "embeddings",
                emb_path,
                Embeddings.get_port(),
                LlamaCppConfig.embeddings_context_size,
                True,  # embedding mode
                None,  # no mmproj for embeddings
                None,  # no chat template
                False,  # not reranking mode
            ),
        ]

        # Start rerank server if configured
        if Rerank.filename:
            try:
                rerank_path = self._resolve_model_path(
                    "rerank", Rerank.filename
                )
                servers.append(
                    (
                        "rerank",
                        rerank_path,
                        Rerank.get_port(),
                        LlamaCppConfig.rerank_context_size,
                        False,  # not embedding mode
                        None,  # no mmproj for rerank
                        None,  # no chat template
                        True,  # reranking mode
                    )
                )
            except RuntimeError:
                logger.warning(
                    "Rerank model configured but not found — skipping rerank server"
                )

        # Start all processes
        for (
            role,
            model_path,
            port,
            ctx_size,
            embedding_mode,
            mmproj,
            tpl_file,
            reranking_mode,
        ) in servers:
            cmd = self._build_run_model_cmd(
                model_path,
                ctx_size,
                port,
                role,
                mmproj,
                embedding_mode,
                tpl_file,
                reranking_mode,
            )
            env = self._get_env_for_run_model()

            logger.info(
                f"Starting {role} server on port {port}: {' '.join(cmd)}"
            )

            proc = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            self._pids[role] = proc.pid

            # Brief check: if the process exits immediately it failed validation
            # (e.g. model file not found, port in use, bad llama-server path).
            time.sleep(2)
            if proc.poll() is not None:
                from aria.config.folders import Debug as DebugConfig

                log_file = DebugConfig.logs_path.parent / f"llama-{role}.log"
                stderr_output = (
                    proc.stderr.read()
                    .decode("utf-8", errors="replace")
                    .strip()
                    if proc.stderr
                    else ""
                )
                raise RuntimeError(
                    f"run-model script for '{role}' exited immediately "
                    f"(exit code {proc.returncode}). "
                    f"llama-server log: {log_file}. "
                    f"run-model stderr: {stderr_output or '(none)'}"
                )

        self._save_pids()

        # Wait for all servers to become ready
        failed = []
        for role, _, port, _, _, _, _, _ in servers:
            logger.info(f"Waiting for {role} server on port {port}...")
            if not self._wait_for_ready(self._host, port):
                failed.append(role)
                logger.error(
                    f"{role} server failed to become ready on port {port}"
                )

        if failed:
            self.stop_all()
            raise RuntimeError(
                f"The following servers failed to start: {', '.join(failed)}. "
                f"Check that the model files exist and the ports are not in use."
            )

        logger.info("All llama-server instances are ready.")

    def stop_all(self, timeout: float = 10.0) -> None:
        """Stop all running llama-server processes.

        Sends SIGTERM, waits for graceful shutdown, then SIGKILL if needed.

        Args:
            timeout: Maximum seconds to wait for graceful shutdown per process.
        """
        for role, pid in list(self._pids.items()):
            if is_process_running(pid):
                logger.info(f"Stopping {role} server (PID {pid})...")
                stop_process(pid, timeout)

        self._clear_pids()
        logger.info("All llama-server instances stopped.")
