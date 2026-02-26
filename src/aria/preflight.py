"""Preflight checks for the Aria web UI.

Verifies that all required dependencies are in place before starting
the Chainlit web server:
  - Required environment variables are set
  - Data folder exists
  - llama-server binary installed
  - run-model script exists
  - All three GGUF models (chat, vl, embeddings) downloaded

Example:
    ```python
    from aria.preflight import run_preflight_checks

    result = run_preflight_checks()
    if not result.passed:
        for failure in result.failures:
            print(f"Missing: {failure.error}")
            print(f"Fix: {failure.hint}")
    ```
"""

import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class CheckResult:
    """Result of a single preflight check.

    Attributes:
        name: Short name of the check (e.g. "llama-server binary").
        passed: True if the check passed, False otherwise.
        category: Group for display (environment, storage, binaries, models, hardware).
        error: Human-readable description of what is missing (if failed).
        hint: Remediation command or instruction for the user (if failed).
        details: Optional extra info to display on success (e.g. "24 GB available").
    """

    name: str
    passed: bool
    category: str = "general"
    error: str = ""
    hint: str = ""
    details: str = ""


@dataclass
class PreflightResult:
    """Result of running all preflight checks.

    Attributes:
        passed: True if all checks passed, False if any failed.
        checks: List of all CheckResult instances.
        failures: List of failed CheckResult instances.
    """

    passed: bool
    checks: List[CheckResult] = field(default_factory=list)

    @property
    def failures(self) -> List[CheckResult]:
        """Return only the failed checks."""
        return [c for c in self.checks if not c.passed]

    def group_by_category(self) -> dict[str, List[CheckResult]]:
        """Group checks by category for display.

        Returns:
            Dict mapping category names to lists of checks.
        """
        grouped: dict[str, List[CheckResult]] = {}
        for check in self.checks:
            if check.category not in grouped:
                grouped[check.category] = []
            grouped[check.category].append(check)
        return grouped


# Required environment variables for the application to start
REQUIRED_ENV_VARS = [
    "DATA_FOLDER",
    "ARIA_DB_FILENAME",
    "LOCAL_STORAGE_PATH",
    "CHROMADB_PERSISTENT_PATH",
    "LLAMA_CPP_BIN_DIR",
    "LLAMA_CPP_VERSION",
    "GGUF_MODELS_DIR",
    "CHAT_OPENAI_API",
    "MAX_ITERATIONS",
    "TOKEN_LIMIT",
    "EMBEDDINGS_API_URL",
    "EMBEDDINGS_MODEL",
    "VL_OPENAI_API",
    "VL_MODEL",
    "CHAINLIT_AUTH_SECRET",
]


def _check_env_vars(checks: List[CheckResult]) -> None:
    """Check that all required environment variables are set."""
    passed = sum(1 for var in REQUIRED_ENV_VARS if os.getenv(var))
    total = len(REQUIRED_ENV_VARS)

    if passed == total:
        checks.append(
            CheckResult(
                name="Environment variables",
                passed=True,
                category="environment",
                details=f"All {total} variables configured",
            )
        )
    else:
        for var in REQUIRED_ENV_VARS:
            if os.getenv(var):
                continue
            checks.append(
                CheckResult(
                    name=f"env:{var}",
                    passed=False,
                    category="environment",
                    error=f"'{var}' is not set",
                    hint=f"Add '{var}' to your .env file",
                )
            )


def _check_data_folder(checks: List[CheckResult]) -> None:
    """Check that the data folder exists."""
    from aria.config.folders import Data

    data_path = Data.path
    if data_path.exists():
        checks.append(
            CheckResult(
                name="Data folder",
                passed=True,
                category="storage",
                details=f"exists at {data_path}",
            )
        )
    else:
        checks.append(
            CheckResult(
                name="Data folder",
                passed=False,
                category="storage",
                error=f"does not exist: {data_path}",
                hint=f"Create the directory: mkdir -p {data_path}",
            )
        )


def _check_binaries(checks: List[CheckResult]) -> None:
    """Check that required binaries exist."""
    from aria.config.api import LlamaCpp as LlamaCppConfig
    from aria.config.folders import Data

    bin_path = LlamaCppConfig.bin_path

    # Check llama-server
    llama_server = bin_path / "llama-server"
    if llama_server.exists():
        checks.append(
            CheckResult(
                name="llama-server",
                passed=True,
                category="binaries",
                details="installed",
            )
        )
    else:
        checks.append(
            CheckResult(
                name="llama-server",
                passed=False,
                category="binaries",
                error=f"not found at {llama_server}",
                hint="Run: aria llamacpp download",
            )
        )

    # Check run-model script
    run_model = Data.path / "bin" / "run-model"
    if run_model.exists():
        checks.append(
            CheckResult(
                name="run-model script",
                passed=True,
                category="binaries",
                details="ready",
            )
        )
    else:
        checks.append(
            CheckResult(
                name="run-model script",
                passed=False,
                category="binaries",
                error=f"not found at {run_model}",
                hint="Ensure data/bin directory contains the run-model script",
            )
        )


def _check_models(checks: List[CheckResult]) -> None:
    """Check that all required GGUF models are downloaded."""
    from aria.config.api import LlamaCpp as LlamaCppConfig
    from aria.config.models import Chat, Embeddings, Vision
    from aria.scripts.gguf import is_model_downloaded

    models_dir = LlamaCppConfig.models_path
    model_checks = [
        ("chat", Chat.filename),
        ("vl", Vision.filename),
        ("embeddings", Embeddings.filename),
    ]

    for alias, filename in model_checks:
        display_name = f"{alias} model"
        if not filename:
            checks.append(
                CheckResult(
                    name=display_name,
                    passed=False,
                    category="models",
                    error="not configured (env var not set)",
                    hint="Set the corresponding env var in your .env file",
                )
            )
            continue

        if is_model_downloaded(filename, models_dir):
            checks.append(
                CheckResult(
                    name=display_name,
                    passed=True,
                    category="models",
                    details=filename,
                )
            )
        else:
            checks.append(
                CheckResult(
                    name=display_name,
                    passed=False,
                    category="models",
                    error=f"not downloaded ({filename})",
                    hint=f"Run: aria models download --model {alias}",
                )
            )


def run_preflight_checks() -> PreflightResult:
    """Run all preflight checks required before starting the web UI.

    Checks performed (all run before returning so every failure is reported):
        1. All required environment variables are set
        2. Data folder exists
        3. llama-server binary exists
        4. run-model script exists
        5. Chat model is downloaded
        6. VL model is downloaded
        7. Embeddings model is downloaded
        8. Memory requirements fit available hardware

    Returns:
        PreflightResult with pass/fail status and all check details.
    """
    checks: List[CheckResult] = []

    _check_env_vars(checks)
    _check_data_folder(checks)
    _check_binaries(checks)
    _check_models(checks)
    _check_memory_requirements(checks)

    return PreflightResult(
        passed=all(c.passed for c in checks),
        checks=checks,
    )


def _detect_compute_platform() -> str:
    """Detect the compute platform: nvidia, metal, or cpu.

    Priority: NVIDIA > Metal > CPU.
    """
    import platform

    # Check for NVIDIA GPU
    try:
        from aria.helpers.nvidia import get_total_vram_mb

        if get_total_vram_mb() > 0:
            return "nvidia"
    except Exception:
        pass

    # Check for Apple Silicon (Metal)
    if platform.system() == "Darwin":
        import subprocess

        try:
            # Check if running on Apple Silicon
            arch = subprocess.check_output(
                ["uname", "-m"], stderr=subprocess.DEVNULL
            ).decode()
            if arch.strip() == "arm64":
                return "metal"
        except Exception:
            pass

    # Fallback to CPU
    return "cpu"


def _check_memory_requirements(checks: List[CheckResult]) -> None:
    """Check if models fit in available GPU VRAM and RAM.

    Platform-aware:
        - NVIDIA: Check VRAM and RAM separately
        - Metal: Use unified memory (system RAM)
        - CPU: Only check system RAM
    """
    from aria.helpers.memory import (
        detect_system_ram,
        get_total_kv_cache_mb,
        get_total_model_size_mb,
    )
    from aria.helpers.nvidia import get_free_vram_per_gpu, get_total_vram_mb

    def _mb_to_gb(mb: int) -> str:
        return f"{mb // 1024} GB"

    # Detect platform
    platform_type = _detect_compute_platform()

    # Check system RAM (all platforms)
    total_ram_mb, avail_ram_mb = detect_system_ram()
    if total_ram_mb > 0:
        checks.append(
            CheckResult(
                name="System RAM",
                passed=True,
                category="hardware",
                details=f"{_mb_to_gb(total_ram_mb)} total",
            )
        )

    # Platform-specific checks
    if platform_type == "nvidia":
        # Check GPU VRAM for NVIDIA
        total_vram = get_total_vram_mb()
        free_vram = get_free_vram_per_gpu()
        if total_vram > 0:
            total_free = sum(free_vram) if free_vram else total_vram
            checks.append(
                CheckResult(
                    name="GPU VRAM",
                    passed=True,
                    category="hardware",
                    details=f"{_mb_to_gb(total_free)} available (NVIDIA)",
                )
            )
    elif platform_type == "metal":
        # Metal uses unified memory
        if total_ram_mb > 0:
            checks.append(
                CheckResult(
                    name="Unified Memory",
                    passed=True,
                    category="hardware",
                    details=f"{_mb_to_gb(total_ram_mb)} (Apple Silicon Metal)",
                )
            )
    else:
        # CPU-only mode
        checks.append(
            CheckResult(
                name="Compute Platform",
                passed=True,
                category="hardware",
                details="CPU-only mode (no GPU acceleration)",
            )
        )

    # Get total model size for memory check
    total_model_mb = get_total_model_size_mb()
    if total_model_mb == 0:
        return  # Models not downloaded, skip remaining checks

    # Platform-specific memory checks
    if platform_type == "nvidia":
        # Check GPU VRAM fits models
        free_vram = get_free_vram_per_gpu()
        if free_vram:
            total_free_vram = sum(free_vram)
            if total_model_mb > total_free_vram:
                checks.append(
                    CheckResult(
                        name="Model memory",
                        passed=False,
                        category="hardware",
                        error=f"Models need {_mb_to_gb(total_model_mb)} but only {_mb_to_gb(total_free_vram)} VRAM available",
                        hint="Use smaller quantization or split models across GPUs",
                    )
                )
    elif platform_type == "metal":
        # Metal: check unified memory (use 70% of total RAM as safe limit)
        safe_memory_mb = int(total_ram_mb * 0.7)
        if total_model_mb > safe_memory_mb:
            checks.append(
                CheckResult(
                    name="Model memory",
                    passed=False,
                    category="hardware",
                    error=f"Models need {_mb_to_gb(total_model_mb)} but only {_mb_to_gb(safe_memory_mb)} safe unified memory available",
                    hint="Use smaller quantization or close other applications",
                )
            )
    else:
        # CPU-only: check available RAM (use 50% as safe limit)
        safe_memory_mb = int(avail_ram_mb * 0.5) if avail_ram_mb > 0 else 0
        if safe_memory_mb > 0 and total_model_mb > safe_memory_mb:
            checks.append(
                CheckResult(
                    name="Model memory",
                    passed=False,
                    category="hardware",
                    error=f"Models need {_mb_to_gb(total_model_mb)} but only {_mb_to_gb(safe_memory_mb)} RAM available for CPU inference",
                    hint="Use smaller quantization or add more RAM",
                )
            )

    # Check system RAM for KV cache (all platforms)
    total_kv_mb = get_total_kv_cache_mb()
    if avail_ram_mb > 0 and total_kv_mb > avail_ram_mb * 0.5:
        checks.append(
            CheckResult(
                name="KV cache memory",
                passed=False,
                category="hardware",
                error=f"KV cache needs ~{_mb_to_gb(total_kv_mb)} but only {_mb_to_gb(avail_ram_mb)} RAM available",
                hint="Reduce context size in configuration",
            )
        )
