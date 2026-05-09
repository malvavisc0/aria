"""vLLM inference server manager.

Manages the vLLM chat process required by the Aria web UI:
  - Chat server (port 9090): ``python -m vllm.entrypoints.openai.api_server``

Process state is persisted to ``data/vllm_servers.json`` so the manager
can track servers started by other processes (e.g. CLI to GUI).

Example:
    ```python
    from aria.server.vllm import VllmServerManager

    manager = VllmServerManager()
    manager.start_all()   # starts chat, waits for /health
    # ... run Chainlit ...
    manager.stop_all()    # graceful shutdown
    ```
"""

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from loguru import logger

from aria.config.folders import Data as DataConfig
from aria.server.process_utils import (
    clear_state,
    is_process_running,
    load_state,
    save_state,
    stop_process_group,
)


class VllmServerManager:
    """Manages vLLM inference server processes for chat.

    All chat servers are launched as
    ``python -m vllm.entrypoints.openai.api_server`` with model-specific flags.

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

    @staticmethod
    def _get_model_max_context(model_path: str) -> int | None:
        """Read the model's maximum context length from its config.json.

        Inspects ``max_position_embeddings``, ``model_max_length``, or
        ``max_seq_len`` fields in the model's config file.

        Args:
            model_path: Local path to the model directory.

        Returns:
            The model's maximum context length, or None if it cannot
            be determined.
        """
        config_path = Path(model_path) / "config.json"
        if not config_path.is_file():
            return None
        try:
            with open(config_path) as f:
                config = json.load(f)
            # Architecture parameters may live at the top level (e.g. Llama,
            # Mistral-7B) or nested inside "text_config" for multimodal /
            # vision models (e.g. Mistral3 / Pixtral, LLaVA).
            text_cfg = config.get("text_config") or {}
            for key in (
                "max_position_embeddings",
                "model_max_length",
                "max_seq_len",
            ):
                val = config.get(key) or text_cfg.get(key)
                if isinstance(val, (int, float)) and val > 0:
                    return int(val)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Could not read model config at {config_path}: {e}")
        return None

    @classmethod
    def _resolve_max_model_len(cls, model_path: str, requested_context: int) -> int:
        """Clamp requested context length to the model's supported maximum."""
        model_max = cls._get_model_max_context(model_path)
        if model_max is not None and requested_context > model_max:
            logger.info(
                f"Clamping max_model_len from {requested_context} to "
                f"{model_max} (model's max_position_embeddings)"
            )
            return model_max
        return requested_context

    @staticmethod
    def _kv_offloading_backend_available(backend: str) -> bool:
        """Return whether the requested KV offloading backend is usable."""
        if backend == "native":
            return True
        if backend == "lmcache":
            return importlib.util.find_spec("lmcache") is not None
        return False

    def _clear_pids(self) -> None:
        """Clear state file and reset in-memory PIDs."""
        self._pids.clear()
        clear_state(self.PID_FILE)

    @staticmethod
    def _find_orphan_pids() -> list[int]:
        """Scan for running vLLM processes not tracked by the PID file.

        Uses ``pgrep`` to find processes matching the vLLM entrypoint
        command pattern. Returns only the group-leader PIDs (lowest PID
        per process group) so that ``stop_process_group`` can kill the
        entire tree.

        Returns:
            Sorted list of vLLM group-leader PIDs found on the system.
        """
        try:
            result = subprocess.run(
                ["pgrep", "-f", "vllm.entrypoints.openai.api_server"],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return []
        except (FileNotFoundError, OSError):
            return []

        pids = [int(p) for p in result.stdout.strip().split("\n") if p.strip()]
        if not pids:
            return []

        # Determine group leaders: for each PID get its PGID, keep only
        # those where PID == PGID (i.e. group leaders started with
        # start_new_session=True).
        leaders: set[int] = set()
        for pid in pids:
            try:
                pgid = os.getpgid(pid)
                leaders.add(pgid)
            except (OSError, ProcessLookupError):
                # Process vanished between pgrep and getpgid
                continue

        return sorted(leaders)

    def _build_vllm_cmd(
        self,
        model_path: str,
        port: int,
        task: str = "auto",
        max_model_len: int | None = None,
        gpu_memory_utilization: float | None = None,
        quantization: str | None = None,
        tensor_parallel_size: int = 1,
        dtype: str = "auto",
        chat_template_file: str | None = None,
        kv_cache_dtype: str = "auto",
        api_key: str = "sk-aria",
        served_model_name: str | None = None,
        tool_call_parser: str | None = None,
        reasoning_parser: str | None = None,
        chat_template_kwargs: str | None = None,
        vision_enabled: bool = False,
        data_parallel_size: int = 1,
        expert_parallel: bool = False,
        mm_encoder_tp_mode: str = "",
        mm_processor_cache_type: str = "",
        prefix_caching: bool = False,
        kv_offload_mode: str = "off",
        kv_offloading_size_gb: float | None = None,
        kv_offloading_backend: str = "native",
    ) -> list[str]:
        """Build command to launch a vLLM server.

        Args:
            model_path: HuggingFace model ID or local path.
            port: Port to run the server on.
            task: vLLM task type (``auto``, ``embed``, ``generate``).
            max_model_len: Maximum sequence length.
            gpu_memory_utilization: Fraction of GPU memory to use (0.0–1.0).
            quantization: Quantization method (e.g. ``gptq``, ``awq``).
            tensor_parallel_size: Number of GPUs for tensor parallelism.
            dtype: Data type (``auto``, ``float16``, ``bfloat16``).
            chat_template_file: Optional Jinja2 chat template file path.
            chat_template_kwargs: JSON string of kwargs for the chat template
                (e.g. ``'{"enable_thinking": true}'``).
            vision_enabled: Enable multi-modal (vision) support. When
                disabled (default), skips the multi-modal warmup to save
                ~6s startup time.
            data_parallel_size: Number of data-parallel replicas.
            expert_parallel: Enable expert parallelism for MoE models.
            mm_encoder_tp_mode: Multi-modal encoder tensor parallelism mode
                (e.g. ``data``).
            mm_processor_cache_type: Multi-modal processor cache type
                (e.g. ``shm`` for shared memory).
            prefix_caching: Enable automatic prefix caching for faster
                inference with shared prompt prefixes.
            kv_offload_mode: KV cache offload strategy (``off``, ``auto``,
                ``ram``).  Default ``off``.
            kv_offloading_size_gb: KV cache offload buffer size in GiB.
                When None and mode is ``auto``/``ram``, calculated at
                launch time.
            kv_offloading_backend: Backend for KV cache offloading
                (``native``, ``lmcache``).  Default ``native``.
        Returns:
            List of command arguments.
        """

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
            cmd.extend(["--gpu-memory-utilization", str(gpu_memory_utilization)])

        effective_quant: str | None = None
        if quantization:
            # vLLM v0.20+: gptq kernel is buggy for 4-bit; use gptq_marlin
            effective_quant = "gptq_marlin" if quantization == "gptq" else quantization
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

        if chat_template_kwargs:
            cmd.extend(["--default-chat-template-kwargs", chat_template_kwargs])

        if data_parallel_size > 1:
            cmd.extend(["--data-parallel-size", str(data_parallel_size)])

        if expert_parallel:
            cmd.extend(["--enable-expert-parallel"])

        if mm_encoder_tp_mode:
            cmd.extend(["--mm-encoder-tp-mode", mm_encoder_tp_mode])

        if mm_processor_cache_type:
            cmd.extend(["--mm-processor-cache-type", mm_processor_cache_type])

        if prefix_caching:
            cmd.extend(["--enable-prefix-caching"])

        # KV cache RAM offloading
        if kv_offload_mode in ("auto", "ram") and kv_offloading_size_gb is not None:
            if kv_offloading_size_gb > 0:
                cmd.extend(["--kv-offloading-size", str(kv_offloading_size_gb)])
                cmd.extend(["--kv-offloading-backend", kv_offloading_backend])
                logger.info(
                    "KV cache offload enabled: {size} GiB via {backend} "
                    "backend (mode={mode})",
                    size=kv_offloading_size_gb,
                    backend=kv_offloading_backend,
                    mode=kv_offload_mode,
                )

        # Override model's generation_config.json (may cap max_tokens too low)
        cmd.extend(["--generation-config", "vllm"])

        if not vision_enabled:
            # Skip multi-modal warmup — saves ~6s startup when not using vision
            cmd.extend(["--limit-mm-per-prompt", '{"image": 0}'])

        # sentence-transformers models often need trust-remote-code
        cmd.extend(["--trust-remote-code"])

        # API key for internal use — must match the client-side api_key
        cmd.extend(["--api-key", api_key])

        return cmd

    def _wait_for_ready(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        proc: subprocess.Popen | None = None,
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

    def start_all(self, force_restart: bool = False) -> None:
        """Start the chat vLLM server process.

        Args:
            force_restart: If True, stop any running vLLM servers before
                starting fresh. Useful for reloading with new config.

        Raises:
            RuntimeError: If the server fails to start or become ready.
        """
        if force_restart and self._pids:
            logger.info("Force restart requested — stopping existing vLLM servers")
            self.stop_all()
        from aria.config.api import Vllm as VllmConfig
        from aria.config.models import Chat

        servers: list[tuple[str, list[str], int]] = []

        # --- Chat server ---
        if not Chat.model_path:
            raise RuntimeError(
                "Chat model path is not configured. "
                "Set CHAT_MODEL_PATH in your .env file."
            )

        # --- Clamp max_model_len to the model's actual maximum ---
        # This must happen BEFORE gpu_memory_utilization calculation so
        # that the KV cache estimate is based on the actual context size.
        max_model_len = VllmConfig.chat_context_size
        max_model_len = self._resolve_max_model_len(Chat.model_path, max_model_len)

        backend = VllmConfig.kv_offloading_backend
        if not isinstance(backend, str) or not backend:
            backend = "native"

        if VllmConfig.kv_offload_mode in (
            "auto",
            "ram",
        ) and not self._kv_offloading_backend_available(backend):
            raise RuntimeError(
                "KV cache offloading backend "
                f"'{backend}' is not available. "
                "Install the required package or set "
                "ARIA_VLLM_KV_OFFLOADING_BACKEND=native."
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
                context_size=max_model_len,
                kv_cache_dtype=VllmConfig.kv_cache_dtype,
            )

        # --- Resolve KV offload size ---
        # Explicit value > auto-calculated from model config > None
        kv_offload_size = VllmConfig.kv_offloading_size_gb
        if VllmConfig.kv_offload_mode in ("auto", "ram") and kv_offload_size is None:
            import math

            from aria.helpers.nvidia import _estimate_kv_cache_mb

            kv_mb = _estimate_kv_cache_mb(
                Chat.model_path,
                max_model_len,
                VllmConfig.kv_cache_dtype,
            )
            if kv_mb is not None and kv_mb > 0:
                kv_offload_size = math.ceil(kv_mb / 1024)  # MiB → GiB
                logger.info(
                    "Auto-calculated KV offload size: {size} GiB "
                    "(estimated KV cache: {kv_mb} MiB)",
                    size=kv_offload_size,
                    kv_mb=kv_mb,
                )

        chat_cmd = self._build_vllm_cmd(
            model_path=Chat.model_path,
            port=Chat.get_port(),
            max_model_len=max_model_len,
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
            chat_template_kwargs=VllmConfig.chat_template_kwargs or None,
            vision_enabled=VllmConfig.vision_enabled,
            data_parallel_size=VllmConfig.data_parallel_size,
            expert_parallel=VllmConfig.expert_parallel,
            mm_encoder_tp_mode=VllmConfig.mm_encoder_tp_mode,
            mm_processor_cache_type=VllmConfig.mm_processor_cache_type,
            prefix_caching=VllmConfig.prefix_caching,
            kv_offload_mode=VllmConfig.kv_offload_mode,
            kv_offloading_size_gb=kv_offload_size,
            kv_offloading_backend=backend,
        )
        servers.append(("chat", chat_cmd, Chat.get_port()))

        # --- Embeddings server (skipped) ---
        # Embeddings are now loaded in-process via HuggingFaceEmbedding.
        # No separate vLLM server is needed.

        from aria.config.folders import Debug as DebugConfig

        # Start all processes with stderr redirected to log files
        procs: dict[str, subprocess.Popen] = {}
        log_files: dict[str, Path] = {}
        for role, cmd, port in servers:
            log_file = DebugConfig.logs_path.parent / f"vllm-{role}.log"
            log_files[role] = log_file
            logger.info(f"Starting {role} server on port {port}: {' '.join(cmd)}")
            logger.info(f"  stderr → {log_file}")

            log_fh = open(log_file, "w")
            from aria.config.folders import get_augmented_env

            proc = subprocess.Popen(
                cmd,
                stdout=log_fh,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                env=get_augmented_env(),
            )
            log_fh.close()
            self._pids[role] = proc.pid
            procs[role] = proc

            # Brief check: if the process exits immediately it failed validation
            time.sleep(3)
            if proc.poll() is not None:
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
            if not self._wait_for_ready(self._host, port, proc=procs.get(role)):
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

    def stop_all(self, timeout: float = 10.0, skip_vllm: bool = False) -> None:
        """Stop all running vLLM server processes.

        Sends SIGTERM to the process group, waits for graceful shutdown,
        then SIGKILL if needed. Falls back to scanning for orphaned vLLM
        processes when the PID file is stale or empty.

        Args:
            timeout: Maximum seconds to wait for graceful shutdown per process.
            skip_vllm: If True, clear PID tracking without killing the
                vLLM processes. The processes will keep running as orphans.
                Useful for rapid web UI restarts without model reload.
        """
        if skip_vllm:
            logger.info("Skipping vLLM shutdown — processes will keep running")
            self._clear_pids()
            return

        killed_pids: set[int] = set()
        survivors: dict[str, int] = {}

        # Phase 1: Stop tracked PIDs from state file
        for role, pid in list(self._pids.items()):
            if is_process_running(pid):
                logger.info(f"Stopping {role} server (PID/PGID {pid})...")
                stopped = stop_process_group(pid, timeout)
                if not stopped and is_process_running(pid):
                    logger.warning(
                        f"{role} server (PID {pid}) did not stop — "
                        "PID preserved for retry"
                    )
                    survivors[role] = pid
                else:
                    killed_pids.add(pid)

        # Phase 2: Scan for orphaned vLLM processes not in the PID file
        orphans = self._find_orphan_pids()
        orphan_leaders = [p for p in orphans if p not in killed_pids]
        if orphan_leaders:
            logger.info(
                f"Found {len(orphan_leaders)} orphaned vLLM process "
                f"group(s): {orphan_leaders}"
            )
            for pid in orphan_leaders:
                if is_process_running(pid):
                    stopped = stop_process_group(pid, timeout)
                    if stopped or not is_process_running(pid):
                        killed_pids.add(pid)
                    else:
                        survivors[f"orphan-{pid}"] = pid

        if survivors:
            self._pids = survivors
            self._save_pids()
            logger.warning(f"Some vLLM processes survived shutdown: {survivors}")
        else:
            self._clear_pids()
            logger.info("All vLLM server instances stopped.")
