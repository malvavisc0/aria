"""vLLM inference server manager.

Manages vLLM processes required by the Aria web UI:
  - Chat server (port 7070): ``python -m vllm.entrypoints.openai.api_server``
  - Embeddings server (port 7072): same entrypoint with ``--task embedding``
  - Rerank server (port 7073): sentence-transformers micro-server on ``:9093``

The VL (vision/language) server is NOT started automatically. It starts
on-demand when the user invokes a vision command (e.g., ``aria vision pdf``).

Process state is persisted to ``data/vllm_servers.json`` so the manager
can track servers started by other processes (e.g. CLI to GUI).

Example:
    ```python
    from aria.server.vllm import VllmServerManager

    manager = VllmServerManager()
    manager.start_all()   # starts chat + embeddings + rerank, waits for /health
    # ... run Chainlit ...
    manager.stop_all()    # graceful shutdown
    ```
"""

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional
from urllib.error import URLError
from urllib.request import urlopen

from loguru import logger

from aria.config.folders import Data as DataConfig
from aria.server.process_utils import (
    clear_state,
    is_process_running,
    load_state,
    save_state,
    stop_process,
)


class VllmServerManager:
    """Manages vLLM inference server processes for chat, embeddings, and rerank.

    All chat/embeddings servers are launched as
    ``python -m vllm.entrypoints.openai.api_server`` with model-specific flags.
    The rerank server is a sentence-transformers FastAPI micro-server.

    The VL (vision/language) server is NOT started automatically.
    It starts on-demand when the user invokes a vision command
    (e.g., ``aria vision pdf`` or ``aria vision image``).

    Process state is persisted to ``data/vllm_servers.json`` so the manager
    can track servers started by other processes (e.g. CLI to GUI).

    Args:
        host: Host address for all servers.

    Example:
        ```python
        manager = VllmServerManager()
        manager.start_all()
        # ... run Chainlit ...
        manager.stop_all()
        ```
    """

    PID_FILE = DataConfig.path / "vllm_servers.json"
    HEALTH_POLL_INTERVAL = 1.0
    HEALTH_TIMEOUT = 300  # vLLM model loading can take longer than llama.cpp

    def __init__(
        self,
        host: str = "0.0.0.0",
    ):
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

    def _build_vllm_cmd(
        self,
        model_path: str,
        port: int,
        role: str,
        task: str = "auto",
        max_model_len: Optional[int] = None,
        gpu_memory_utilization: Optional[float] = None,
        quantization: Optional[str] = None,
        tensor_parallel_size: int = 1,
        dtype: str = "auto",
        chat_template_file: Optional[str] = None,
        kv_cache_dtype: str = "auto",
        api_key: str = "sk-aria",
        served_model_name: Optional[str] = None,
        tool_call_parser: Optional[str] = None,
        reasoning_parser: Optional[str] = None,
    ) -> list[str]:
        """Build command to launch a vLLM server.

        Args:
            model_path: HuggingFace model ID or local path.
            port: Port to run the server on.
            role: Server role name (chat/embeddings), used for log naming.
            task: vLLM task type (``auto``, ``embed``, ``generate``).
            max_model_len: Maximum sequence length.
            gpu_memory_utilization: Fraction of GPU memory to use (0.0–1.0).
            quantization: Quantization method (e.g. ``gptq``, ``awq``).
            tensor_parallel_size: Number of GPUs for tensor parallelism.
            dtype: Data type (``auto``, ``float16``, ``bfloat16``).
            chat_template_file: Optional Jinja2 chat template file path.

        Returns:
            List of command arguments.
        """
        from aria.config.folders import Debug as DebugConfig

        log_file = DebugConfig.logs_path.parent / f"vllm-{role}.log"

        cmd = [
            sys.executable,
            "-m",
            "vllm.entrypoints.openai.api_server",
            "--model",
            model_path,
            "--port",
            str(port),
            "--host",
            self._host,
        ]

        if task == "embed":
            cmd.extend(["--runner", "pooling", "--convert", "embed"])
        elif task and task != "auto":
            cmd.extend(["--convert", task])

        if max_model_len:
            cmd.extend(["--max-model-len", str(max_model_len)])

        if gpu_memory_utilization is not None:
            cmd.extend(
                ["--gpu-memory-utilization", str(gpu_memory_utilization)]
            )

        effective_quant: Optional[str] = None
        if quantization:
            # vLLM v0.20+: gptq kernel is buggy for 4-bit; use gptq_marlin
            effective_quant = (
                "gptq_marlin" if quantization == "gptq" else quantization
            )
            cmd.extend(["--quantization", effective_quant])

        # Resolve dtype: GPTQ only supports float16
        effective_dtype = dtype
        if (
            effective_quant is not None
            and effective_quant.startswith("gptq")
            and dtype == "auto"
        ):
            effective_dtype = "float16"
        cmd.extend(["--dtype", effective_dtype])

        if tensor_parallel_size > 1:
            cmd.extend(["--tensor-parallel-size", str(tensor_parallel_size)])

        if chat_template_file and task != "embed":
            cmd.extend(["--chat-template", chat_template_file])

        if kv_cache_dtype and kv_cache_dtype != "auto":
            cmd.extend(["--kv-cache-dtype", kv_cache_dtype])
            if kv_cache_dtype.startswith("fp8"):
                # FlashAttention v2 doesn't support fp8 KV cache — switch to FlashInfer
                cmd.extend(["--attention-backend", "flashinfer"])

        if served_model_name:
            cmd.extend(["--served-model-name", served_model_name])

        if tool_call_parser:
            cmd.extend(
                [
                    "--enable-auto-tool-choice",
                    "--tool-call-parser",
                    tool_call_parser,
                ]
            )

        if reasoning_parser:
            cmd.extend(["--reasoning-parser", reasoning_parser])

        # sentence-transformers models often need trust-remote-code
        cmd.extend(["--trust-remote-code"])

        # API key for internal use — must match the client-side api_key
        cmd.extend(["--api-key", api_key])

        return cmd

    def _wait_for_ready(
        self,
        host: str,
        port: int,
        timeout: Optional[float] = None,
        proc: Optional[subprocess.Popen] = None,
    ) -> bool:
        """Poll ``/health`` until the server returns HTTP 200 or timeout.

        Also checks if the process is still alive — if it exits before
        becoming healthy, returns False immediately.

        Args:
            host: Server host.
            port: Server port.
            timeout: Maximum seconds to wait (default: ``HEALTH_TIMEOUT``).
            proc: Optional subprocess to check for early exit.

        Returns:
            True if the server became ready, False if timed out or crashed.
        """
        if timeout is None:
            timeout = self.HEALTH_TIMEOUT

        url = f"http://{host}:{port}/health"
        deadline = time.time() + timeout

        while time.time() < deadline:
            # Check if process crashed
            if proc is not None and proc.poll() is not None:
                return False

            try:
                with urlopen(url, timeout=2) as resp:
                    if resp.status == 200:
                        return True
            except (URLError, OSError):
                pass
            time.sleep(self.HEALTH_POLL_INTERVAL)

        return False

    def start_all(self) -> None:
        """Start chat and embeddings vLLM server processes.

        The VL (vision/language) server is NOT started automatically.
        It starts on-demand when the user invokes a vision command.

        The rerank server is started if a rerank model is configured
        and sentence-transformers is installed.

        Raises:
            RuntimeError: If any server fails to start or become ready.
        """
        from aria.config.api import Vllm as VllmConfig
        from aria.config.models import Chat, Rerank

        servers: list[tuple[str, list[str], int]] = []

        # --- Chat server ---
        if not Chat.model_path:
            raise RuntimeError(
                "Chat model path is not configured. "
                "Set CHAT_MODEL_PATH in your .env file."
            )

        # --- Auto-calculate gpu_memory_utilization if not explicitly set ---
        gpu_mem = VllmConfig.gpu_memory_utilization
        if gpu_mem is None:
            from aria.helpers.nvidia import (
                calculate_gpu_memory_utilization,
                get_total_vram_mb,
            )

            total_vram = get_total_vram_mb()
            gpu_mem = calculate_gpu_memory_utilization(
                total_vram_mb=total_vram,
                model_path=Chat.model_path,
                context_size=VllmConfig.chat_context_size,
                kv_cache_dtype=VllmConfig.kv_cache_dtype,
            )

        chat_cmd = self._build_vllm_cmd(
            model_path=Chat.model_path,
            port=Chat.get_port(),
            role="chat",
            max_model_len=VllmConfig.chat_context_size,
            gpu_memory_utilization=gpu_mem,
            quantization=VllmConfig.quantization,
            tensor_parallel_size=VllmConfig.tensor_parallel_size,
            dtype=VllmConfig.dtype,
            chat_template_file=(
                str(VllmConfig.chat_template_file)
                if VllmConfig.chat_template_file
                else None
            ),
            kv_cache_dtype=VllmConfig.kv_cache_dtype,
            api_key=VllmConfig.api_key,
            served_model_name=Chat.model,
            tool_call_parser=VllmConfig.tool_call_parser,
            reasoning_parser=VllmConfig.reasoning_parser,
        )
        servers.append(("chat", chat_cmd, Chat.get_port()))

        # --- Embeddings server (skipped) ---
        # Embeddings are now loaded in-process via HuggingFaceEmbedding.
        # No separate vLLM server is needed.

        # --- Rerank server (optional) ---
        if Rerank.model_path:
            try:
                rerank_port = Rerank.get_port()
                rerank_cmd = self._build_rerank_cmd(
                    model_path=Rerank.model_path,
                    port=rerank_port,
                )
                servers.append(("rerank", rerank_cmd, rerank_port))
            except Exception as exc:
                logger.warning(
                    f"Rerank model configured but could not start: {exc} — "
                    "skipping rerank server"
                )

        from aria.config.folders import Debug as DebugConfig

        # Start all processes with stderr redirected to log files
        procs: dict[str, subprocess.Popen] = {}
        log_files: dict[str, Path] = {}
        for role, cmd, port in servers:
            log_file = DebugConfig.logs_path.parent / f"vllm-{role}.log"
            log_files[role] = log_file
            logger.info(
                f"Starting {role} server on port {port}: {' '.join(cmd)}"
            )
            logger.info(f"  stderr → {log_file}")

            log_fh = open(log_file, "w")
            proc = subprocess.Popen(
                cmd,
                stdout=log_fh,
                stderr=subprocess.STDOUT,
            )
            self._pids[role] = proc.pid
            procs[role] = proc

            # Brief check: if the process exits immediately it failed validation
            time.sleep(3)
            if proc.poll() is not None:
                log_fh.close()
                stderr_output = ""
                if log_file.exists():
                    stderr_output = log_file.read_text().strip()[-2000:]
                raise RuntimeError(
                    f"vLLM server for '{role}' exited immediately "
                    f"(exit code {proc.returncode}). "
                    f"Log: {log_file}\n"
                    f"stderr: {stderr_output or '(none)'}"
                )

        self._save_pids()

        # Wait for all servers to become ready
        failed = []
        for role, _, port in servers:
            logger.info(f"Waiting for {role} server on port {port}...")
            if not self._wait_for_ready(
                self._host, port, proc=procs.get(role)
            ):
                failed.append(role)
                log_tail = ""
                lf = log_files.get(role)
                if lf and lf.exists():
                    log_tail = lf.read_text().strip()[-2000:]
                logger.error(
                    f"{role} server failed to become ready on port {port}. "
                    f"Log: {lf}\n"
                    f"Last output: {log_tail or '(empty)'}"
                )

        if failed:
            self.stop_all()
            raise RuntimeError(
                f"The following servers failed to start: {', '.join(failed)}. "
                f"Check logs: {', '.join(str(log_files[f]) for f in failed)}"
            )

        logger.info("All vLLM server instances are ready.")

    def _build_rerank_cmd(
        self,
        model_path: str,
        port: int,
    ) -> list[str]:
        """Build command to launch the rerank micro-server.

        Args:
            model_path: HuggingFace model ID for the rerank model.
            port: Port for the rerank server.

        Returns:
            List of command arguments.
        """
        from aria.config.folders import Debug as DebugConfig

        log_file = DebugConfig.logs_path.parent / "vllm-rerank.log"

        # Use the rerank module directly
        cmd = [
            sys.executable,
            "-m",
            "aria.server.rerank",
            "--model",
            model_path,
            "--port",
            str(port),
            "--host",
            self._host,
        ]
        return cmd

    def stop_all(self, timeout: float = 10.0) -> None:
        """Stop all running vLLM server processes.

        Sends SIGTERM, waits for graceful shutdown, then SIGKILL if needed.

        Args:
            timeout: Maximum seconds to wait for graceful shutdown per process.
        """
        for role, pid in list(self._pids.items()):
            if is_process_running(pid):
                logger.info(f"Stopping {role} server (PID {pid})...")
                stop_process(pid, timeout)

        self._clear_pids()
        logger.info("All vLLM server instances stopped.")
