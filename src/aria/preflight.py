"""Preflight checks for the Aria web UI.

Verifies that all required dependencies are in place before starting
the Chainlit web server:
  - llama-server binary installed in the configured bin directory
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
class FailedCheck:
    """A single failed preflight check.

    Attributes:
        name: Short name of the check (e.g. "llama-server binary").
        error: Human-readable description of what is missing.
        hint: Remediation command or instruction for the user.
    """

    name: str
    error: str
    hint: str


@dataclass
class PreflightResult:
    """Result of running all preflight checks.

    Attributes:
        passed: True if all checks passed, False if any failed.
        failures: List of FailedCheck instances for each failed check.
            Empty when passed is True.
    """

    passed: bool
    failures: List[FailedCheck] = field(default_factory=list)


def run_preflight_checks() -> PreflightResult:
    """Run all preflight checks required before starting the web UI.

    Checks performed (all run before returning so every failure is reported):
        1. llama-server binary exists in LlamaCppConfig.bin_path
        2. Chat model is downloaded (CHAT_MODEL / CHAT_MODEL_TYPE env vars)
        3. VL model is downloaded (VL_MODEL / VL_MODEL_TYPE env vars)
        4. Embeddings model is downloaded (EMBEDDINGS_MODEL / EMBEDDINGS_MODEL_TYPE env vars)

    Returns:
        PreflightResult with pass/fail status and structured failure details.
    """
    from aria.config.api import LlamaCpp as LlamaCppConfig
    from aria.scripts.gguf import is_model_downloaded

    failures: List[FailedCheck] = []

    # --- Check 1: llama-server binary ---
    llama_server_path: Path = LlamaCppConfig.bin_path / "llama-server"
    if not llama_server_path.exists():
        failures.append(
            FailedCheck(
                name="llama-server binary",
                error=f"llama-server not found at: {llama_server_path}",
                hint="Run: aria llamacpp download",
            )
        )

    # --- Checks 2-4: GGUF models ---
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
            failures.append(
                FailedCheck(
                    name=f"{alias} model",
                    error=f"Model '{alias}' is not configured (env var not set).",
                    hint="Set the corresponding env var in your .env file.",
                )
            )
            continue

        if not is_model_downloaded(repo_id, quantization, models_dir):
            failures.append(
                FailedCheck(
                    name=f"{alias} model",
                    error=(
                        f"Model '{alias}' ({repo_id} / {quantization}) "
                        f"is not downloaded."
                    ),
                    hint=f"Run: aria models download --model {alias}",
                )
            )

    return PreflightResult(
        passed=len(failures) == 0,
        failures=failures,
    )
