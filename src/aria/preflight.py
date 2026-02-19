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
from pathlib import Path
from typing import List


@dataclass
class CheckResult:
    """Result of a single preflight check.

    Attributes:
        name: Short name of the check (e.g. "llama-server binary").
        passed: True if the check passed, False otherwise.
        error: Human-readable description of what is missing (if failed).
        hint: Remediation command or instruction for the user (if failed).
    """

    name: str
    passed: bool
    error: str = ""
    hint: str = ""


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
    for var in REQUIRED_ENV_VARS:
        if os.getenv(var):
            checks.append(CheckResult(name=f"env:{var}", passed=True))
        else:
            checks.append(
                CheckResult(
                    name=f"env:{var}",
                    passed=False,
                    error=f"Environment variable '{var}' is not set.",
                    hint=f"Add '{var}' to your .env file.",
                )
            )


def _check_data_folder(checks: List[CheckResult]) -> None:
    """Check that the data folder exists."""
    from aria.config.folders import Data

    data_path = Data.path
    if data_path.exists():
        checks.append(CheckResult(name="data folder", passed=True))
    else:
        checks.append(
            CheckResult(
                name="data folder",
                passed=False,
                error=f"Data folder does not exist: {data_path}",
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
        checks.append(CheckResult(name="llama-server binary", passed=True))
    else:
        checks.append(
            CheckResult(
                name="llama-server binary",
                passed=False,
                error=f"llama-server not found at: {llama_server}",
                hint="Run: aria llamacpp download",
            )
        )

    # Check run-model script
    run_model = Data.path / "bin" / "run-model"
    if run_model.exists():
        checks.append(CheckResult(name="run-model script", passed=True))
    else:
        checks.append(
            CheckResult(
                name="run-model script",
                passed=False,
                error=f"run-model script not found at: {run_model}",
                hint="Ensure the data/bin directory contains the run-model script.",
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
        if not filename:
            checks.append(
                CheckResult(
                    name=f"{alias} model",
                    passed=False,
                    error=f"Model '{alias}' is not configured (env var not set).",
                    hint="Set the corresponding env var in your .env file.",
                )
            )
            continue

        if is_model_downloaded(filename, models_dir):
            checks.append(CheckResult(name=f"{alias} model", passed=True))
        else:
            checks.append(
                CheckResult(
                    name=f"{alias} model",
                    passed=False,
                    error=f"Model '{alias}' ({filename}) is not downloaded.",
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


def _check_memory_requirements(checks: List[CheckResult]) -> None:
    """Check if models fit in available GPU VRAM and RAM."""
    from aria.helpers.memory import (
        detect_system_ram,
        get_total_kv_cache_mb,
        get_total_model_size_mb,
    )
    from aria.helpers.nvidia import get_free_vram_per_gpu, get_total_vram_mb

    # Minimum hardware requirements
    MIN_VRAM_MB = 8192  # 8 GB
    MIN_RAM_MB = 8192  # 16 GB

    # Check minimum VRAM
    total_vram = get_total_vram_mb()
    if total_vram > 0 and total_vram < MIN_VRAM_MB:
        checks.append(
            CheckResult(
                name="GPU VRAM (minimum)",
                passed=False,
                error=f"GPU has {total_vram} MB VRAM, minimum required is {MIN_VRAM_MB} MB",
                hint="A GPU with at least 8 GB VRAM is required",
            )
        )

    # Check minimum RAM
    total_ram_mb, _ = detect_system_ram()
    if total_ram_mb > 0 and total_ram_mb < MIN_RAM_MB:
        checks.append(
            CheckResult(
                name="System RAM (minimum)",
                passed=False,
                error=f"System has {total_ram_mb} MB RAM, minimum required is {MIN_RAM_MB} MB",
                hint="At least 8 GB RAM is required",
            )
        )

    # Get total model size
    total_model_mb = get_total_model_size_mb()
    if total_model_mb == 0:
        return  # Models not downloaded, skip remaining checks

    # Check GPU VRAM fits models
    free_vram = get_free_vram_per_gpu()
    if free_vram:
        total_free_vram = sum(free_vram)
        if total_model_mb > total_free_vram:
            checks.append(
                CheckResult(
                    name="GPU VRAM",
                    passed=False,
                    error=f"Models require {total_model_mb} MB but only {total_free_vram} MB VRAM available",
                    hint="Use smaller quantization (Q4_K_M) or split models across GPUs",
                )
            )
        else:
            checks.append(CheckResult(name="GPU VRAM", passed=True))

    # Check system RAM for KV cache
    total_kv_mb = get_total_kv_cache_mb()
    _, avail_ram_mb = detect_system_ram()
    if avail_ram_mb > 0 and total_kv_mb > avail_ram_mb * 0.5:
        checks.append(
            CheckResult(
                name="System RAM",
                passed=False,
                error=f"KV cache requires ~{total_kv_mb} MB but only {avail_ram_mb} MB RAM available",
                hint="Reduce context size in configuration",
            )
        )
    elif avail_ram_mb > 0:
        checks.append(CheckResult(name="System RAM", passed=True))
