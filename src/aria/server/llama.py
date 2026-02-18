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

import json
import os
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.error import URLError
from urllib.request import urlopen

from loguru import logger

import aria
from aria.config.api import LlamaCpp as LlamaCppConfig
from aria.config.folders import Data as DataConfig


@dataclass
class LlamaCppServerConfig:
    """Configuration for a single llama-server instance.

    Attributes:
        role: Server role — ``"chat"``, ``"vl"``, or ``"embeddings"``.
        model_path: Absolute path to the ``.gguf`` model file.
        host: Host address to bind to (e.g. ``"0.0.0.0"``).
        port: Port number to listen on.
        context_size: Token context window size (``--ctx-size``).
        gpu_layers: Number of layers to offload to GPU (``--n-gpu-layers``).
        use_run_model: If True, launch via the ``run-model`` script.
                       If False, launch directly with ``llama-server --embedding``.
    """

    role: str
    model_path: Path
    host: str
    port: int
    context_size: int
    gpu_layers: int
    use_run_model: bool


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
        self._processes: dict[str, subprocess.Popen] = {}
        self._pids: dict[str, int] = {}
        self._load_state()

    # -------------------------------------------------------------------------
    # State persistence
    # -------------------------------------------------------------------------

    def _load_state(self) -> None:
        """Load process state from the PID file."""
        if not self.PID_FILE.exists():
            return
        try:
            with open(self.PID_FILE) as f:
                data = json.load(f)
            for role, pid in data.items():
                if isinstance(pid, int) and self._is_process_running(pid):
                    self._pids[role] = pid
        except (json.JSONDecodeError, KeyError, ValueError):
            pass

    def _save_state(self) -> None:
        """Save process state to the PID file."""
        self.PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        pids = {}
        for role, proc in self._processes.items():
            pids[role] = proc.pid
        for role, pid in self._pids.items():
            if role not in pids:
                pids[role] = pid
        with open(self.PID_FILE, "w") as f:
            json.dump(pids, f, indent=2)

    def _clear_state(self) -> None:
        """Clear the PID file and reset in-memory state."""
        self._pids.clear()
        if self.PID_FILE.exists():
            self.PID_FILE.unlink()

    # -------------------------------------------------------------------------
    # Process utilities
    # -------------------------------------------------------------------------

    @staticmethod
    def _is_process_running(pid: int) -> bool:
        """Check if a process with the given PID is running."""
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    # -------------------------------------------------------------------------
    # Config building
    # -------------------------------------------------------------------------

    def build_configs(self) -> list[LlamaCppServerConfig]:
        """Build server configs for all three roles.

        Resolves model file paths from ``LlamaCppConfig.models_path`` using
        ``get_model_path()`` from ``aria.scripts.gguf``.

        Returns:
            List of ``LlamaCppServerConfig`` instances (chat, vl, embeddings).

        Raises:
            RuntimeError: If a model file cannot be found.
        """
        from aria.config.models import Chat, Embeddings, Vision
        from aria.scripts.gguf import get_model_path

        models_dir = LlamaCppConfig.models_path
        configs = []

        role_map = [
            (
                "chat",
                Chat.repo_id,
                Chat.quantization,
                Chat.get_port(),
                True,
                self._context_size,
            ),
            (
                "vl",
                Vision.repo_id,
                Vision.quantization,
                Vision.get_port(),
                True,
                self._context_size,
            ),
            (
                "embeddings",
                Embeddings.repo_id,
                Embeddings.quantization,
                Embeddings.get_port(),
                False,
                self.EMBEDDINGS_CTX_SIZE,
            ),
        ]

        for (
            role,
            repo_id,
            quantization,
            port,
            use_run_model,
            ctx_size,
        ) in role_map:
            if not repo_id:
                raise RuntimeError(
                    f"Model repo_id for role '{role}' is not configured. "
                    f"Set the corresponding env var in your .env file."
                )
            model_path = get_model_path(repo_id, quantization, models_dir)
            if model_path is None:
                raise RuntimeError(
                    f"Model file for role '{role}' ({repo_id} / {quantization}) "
                    f"not found in {models_dir}. Run: aria models download --model {role}"
                )
            configs.append(
                LlamaCppServerConfig(
                    role=role,
                    model_path=model_path,
                    host=self._host,
                    port=port,
                    context_size=ctx_size,
                    gpu_layers=self._gpu_layers,
                    use_run_model=use_run_model,
                )
            )

        return configs

    # -------------------------------------------------------------------------
    # Command builders
    # -------------------------------------------------------------------------

    def _build_run_model_cmd(self, config: LlamaCppServerConfig) -> list[str]:
        """Build the command to launch a chat/VL server via ``run-model``.

        Sets ``LLAMA_SERVER_PATH`` so the script finds the correct binary.
        """
        return [
            str(self.RUN_MODEL_SCRIPT),
            str(config.model_path),
            str(config.context_size),
            "--port",
            str(config.port),
        ]

    def _build_embedding_cmd(self, config: LlamaCppServerConfig) -> list[str]:
        """Build the command to launch the embeddings server directly."""
        llama_server = str(LlamaCppConfig.bin_path / "llama-server")
        return [
            llama_server,
            "--model",
            str(config.model_path),
            "--embedding",
            "--ctx-size",
            str(config.context_size),
            "--threads",
            str(os.cpu_count() or 4),
            "--n-gpu-layers",
            str(config.gpu_layers),
            "--parallel",
            str(self.EMBEDDINGS_PARALLEL),
            "--host",
            config.host,
            "--port",
            str(config.port),
        ]

    def _get_env_for_run_model(self) -> dict:
        """Build the environment for the run-model script."""
        env = os.environ.copy()
        env["LLAMA_SERVER_PATH"] = str(
            LlamaCppConfig.bin_path / "llama-server"
        )
        return env

    # -------------------------------------------------------------------------
    # Health check
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    def start_all(self) -> None:
        """Start all three llama-server processes and wait for them to be ready.

        Raises:
            RuntimeError: If any server fails to start or become ready.
        """
        configs = self.build_configs()

        # Start all processes in parallel
        for config in configs:
            if config.use_run_model:
                cmd = self._build_run_model_cmd(config)
                env = self._get_env_for_run_model()
            else:
                cmd = self._build_embedding_cmd(config)
                env = os.environ.copy()

            logger.info(
                f"Starting {config.role} server on port {config.port}: {' '.join(cmd)}"
            )

            proc = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._processes[config.role] = proc

        self._save_state()

        # Wait for all servers to become ready
        failed = []
        for config in configs:
            logger.info(
                f"Waiting for {config.role} server on port {config.port}..."
            )
            if not self._wait_for_ready(config.host, config.port):
                failed.append(config.role)
                logger.error(
                    f"{config.role} server failed to become ready on port {config.port}"
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
        # Stop processes we started in this session
        for role, proc in list(self._processes.items()):
            if proc.poll() is None:
                logger.info(f"Stopping {role} server (PID {proc.pid})...")
                proc.terminate()
                try:
                    proc.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    logger.warning(
                        f"Force-killing {role} server (PID {proc.pid})"
                    )
                    proc.kill()
                    proc.wait()

        # Stop processes tracked from PID file (started by another instance)
        for role, pid in list(self._pids.items()):
            if role not in self._processes and self._is_process_running(pid):
                logger.info(
                    f"Stopping {role} server (PID {pid}) from PID file..."
                )
                try:
                    os.kill(pid, signal.SIGTERM)
                    start = time.time()
                    while time.time() - start < timeout:
                        if not self._is_process_running(pid):
                            break
                        time.sleep(0.1)
                    else:
                        os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

        self._processes.clear()
        self._clear_state()
        logger.info("All llama-server instances stopped.")

    def is_all_running(self) -> bool:
        """Check if all three server processes are alive.

        Returns:
            True if all three servers are running, False otherwise.
        """
        roles = {"chat", "vl", "embeddings"}

        for role in roles:
            proc = self._processes.get(role)
            if proc is not None:
                if proc.poll() is not None:
                    return False
                continue

            pid = self._pids.get(role)
            if pid is None or not self._is_process_running(pid):
                return False

        return True

    def get_pids(self) -> dict[str, Optional[int]]:
        """Get the PIDs of all managed server processes.

        Returns:
            Dict mapping role name to PID (or None if not running).
        """
        result: dict[str, Optional[int]] = {}
        for role in ("chat", "vl", "embeddings"):
            proc = self._processes.get(role)
            if proc is not None:
                result[role] = proc.pid
            else:
                result[role] = self._pids.get(role)
        return result
