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
    data_folder = os.getenv("DATA_FOLDER")
    if not data_folder:
        return  # Already caught by env var check

    data_path = Path.cwd() / data_folder
    if data_path.exists():
        checks.append(CheckResult(name="data folder", passed=True))
    else:
        checks.append(
            CheckResult(
                name="data folder",
                passed=False,
                error=f"Data folder does not exist: {data_path}",
                hint=f"Create the directory: mkdir -p {data_folder}",
            )
        )


def _check_binaries(checks: List[CheckResult]) -> None:
    """Check that required binaries exist."""
    data_folder = os.getenv("DATA_FOLDER")
    bin_dir = os.getenv("LLAMA_CPP_BIN_DIR")

    if not data_folder or not bin_dir:
        return  # Already caught by env var check

    bin_path = Path.cwd() / data_folder / bin_dir

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
    run_model = Path.cwd() / data_folder / "bin" / "run-model"
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
    from aria.scripts.gguf import is_model_downloaded

    models_dir = LlamaCppConfig.models_path
    model_checks = [
        (
            "chat",
            os.getenv("CHAT_MODEL", ""),
            os.getenv("CHAT_MODEL_TYPE", "Q8_0"),
        ),
        (
            "vl",
            os.getenv("VL_MODEL", ""),
            os.getenv("VL_MODEL_TYPE", "Q8_0"),
        ),
        (
            "embeddings",
            os.getenv("EMBEDDINGS_MODEL", ""),
            os.getenv("EMBEDDINGS_MODEL_TYPE", "Q8_0"),
        ),
    ]

    for alias, repo_id, quantization in model_checks:
        if not repo_id:
            checks.append(
                CheckResult(
                    name=f"{alias} model",
                    passed=False,
                    error=f"Model '{alias}' is not configured (env var not set).",
                    hint="Set the corresponding env var in your .env file.",
                )
            )
            continue

        if is_model_downloaded(repo_id, quantization, models_dir):
            checks.append(CheckResult(name=f"{alias} model", passed=True))
        else:
            checks.append(
                CheckResult(
                    name=f"{alias} model",
                    passed=False,
                    error=f"Model '{alias}' ({repo_id} / {quantization}) is not downloaded.",
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

    Returns:
        PreflightResult with pass/fail status and all check details.
    """
    checks: List[CheckResult] = []

    _check_env_vars(checks)
    _check_data_folder(checks)
    _check_binaries(checks)
    _check_models(checks)

    return PreflightResult(
        passed=all(c.passed for c in checks),
        checks=checks,
    )
