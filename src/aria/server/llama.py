"""LlamaCPP inference server manager.

Manages three llama-server processes required by the Aria web UI:
  - Chat server (port 7070): launched via the bundled ``run-model`` script
  - Vision/Language server (port 7071): launched via the bundled ``run-model`` script
  - Embeddings server (port 7072): launched directly with ``llama-server --embedding``

The ``run-model`` script handles GPU detection, KV cache tuning, flash attention,
and dual-GPU configuration automatically for the chat and VL servers.

Example:
    ```python
    from aria.server.llama import LlamaCppServerManager

    manager = LlamaCppServerManager(context_size=8192)
    manager.start_all()   # starts all three servers, waits for /health
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
    """Manages the llama-server processes for chat, VL, and embeddings.

    Chat and VL servers are launched via the bundled ``data/bin/run-model``
    script which handles GPU detection, KV cache tuning, and flash attention.

    The embeddings server is launched directly with ``llama-server --embedding``
    since it requires different flags (``--parallel``, no temperature/top-p).

    Process state is persisted to ``data/llama_servers.json`` so the manager
    can track servers started by other processes (e.g. CLI to GUI).

    Args:
        context_size: Token context window for chat and VL servers.
                      Embeddings server always uses 4096.
        gpu_layers: Number of GPU layers (default 999 = all layers on GPU).
        host: Host address for all servers.

    Example:
        ```python
        manager = LlamaCppServerManager(context_size=16384)
        manager.start_all()
        # ... run Chainlit ...
        manager.stop_all()
        ```
    """

    PID_FILE = DataConfig.path / "llama_servers.json"
    RUN_MODEL_SCRIPT = DataConfig.path / "bin" / "run-model"
    EMBEDDINGS_CTX_SIZE = 4096
    EMBEDDINGS_PARALLEL = 4
    HEALTH_POLL_INTERVAL = 0.5
    HEALTH_TIMEOUT = 120  # seconds

    def __init__(
        self,
        context_size: int = 8192,
        gpu_layers: int = 999,
        host: str = "0.0.0.0",
    ):
        self._context_size = context_size
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

    def _resolve_model_path(
        self, role: str, repo_id: str, quantization: str
    ) -> Path:
        """Resolve model path, raising RuntimeError if not found."""
        from aria.scripts.gguf import get_model_path

        if not repo_id:
            raise RuntimeError(
                f"Model repo_id for role '{role}' is not configured. "
                f"Set the corresponding env var in your .env file."
            )

        models_dir = LlamaCppConfig.models_path
        model_path = get_model_path(repo_id, quantization, models_dir)

        if model_path is None:
            raise RuntimeError(
                f"Model file for role '{role}' ({repo_id} / {quantization}) "
                f"not found in {models_dir}. Run: aria models download --model {role}"
            )

        return model_path

    def _build_run_model_cmd(
        self, model_path: Path, context_size: int, port: int
    ) -> list[str]:
        """Build command to launch a chat/VL server via run-model script."""
        return [
            str(self.RUN_MODEL_SCRIPT),
            str(model_path),
            str(context_size),
            "--port",
            str(port),
        ]

    def _build_embedding_cmd(self, model_path: Path, port: int) -> list[str]:
        """Build command to launch the embeddings server directly."""
        llama_server = str(LlamaCppConfig.bin_path / "llama-server")
        return [
            llama_server,
            "--model",
            str(model_path),
            "--embedding",
            "--ctx-size",
            str(self.EMBEDDINGS_CTX_SIZE),
            "--threads",
            str(os.cpu_count() or 4),
            "--n-gpu-layers",
            str(self._gpu_layers),
            "--parallel",
            str(self.EMBEDDINGS_PARALLEL),
            "--host",
            self._host,
            "--port",
            str(port),
        ]

    def _get_env_for_run_model(self) -> dict:
        """Build environment for the run-model script."""
        env = os.environ.copy()
        env["LLAMA_SERVER_PATH"] = str(
            LlamaCppConfig.bin_path / "llama-server"
        )
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
        """Start all three llama-server processes and wait for them to be ready.

        Raises:
            RuntimeError: If any server fails to start or become ready.
        """
        from aria.config.models import Chat, Embeddings, Vision

        # Resolve model paths
        chat_path = self._resolve_model_path(
            "chat", Chat.repo_id, Chat.quantization
        )
        vl_path = self._resolve_model_path(
            "vl", Vision.repo_id, Vision.quantization
        )
        emb_path = self._resolve_model_path(
            "embeddings", Embeddings.repo_id, Embeddings.quantization
        )

        servers = [
            ("chat", chat_path, Chat.get_port(), self._context_size, True),
            ("vl", vl_path, Vision.get_port(), self._context_size, True),
            (
                "embeddings",
                emb_path,
                Embeddings.get_port(),
                self.EMBEDDINGS_CTX_SIZE,
                False,
            ),
        ]

        # Start all processes
        for role, model_path, port, ctx_size, use_run_model in servers:
            if use_run_model:
                cmd = self._build_run_model_cmd(model_path, ctx_size, port)
                env = self._get_env_for_run_model()
            else:
                cmd = self._build_embedding_cmd(model_path, port)
                env = os.environ.copy()

            logger.info(
                f"Starting {role} server on port {port}: {' '.join(cmd)}"
            )

            proc = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._pids[role] = proc.pid

        self._save_pids()

        # Wait for all servers to become ready
        failed = []
        for role, _, port, _, _ in servers:
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
