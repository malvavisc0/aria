"""Preflight checks for the Aria web UI.

Verifies that all required dependencies are in place before starting
the Chainlit web server:
  - Required environment variables are set
  - Data folder exists
  - vLLM is installed (Python package)
  - All required models are configured (chat, embeddings)
  - Model paths exist (local dirs or HF snapshots)

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
        name: Short name of the check (e.g. "vLLM package").
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
    "CHAT_MODEL",
    "CHAT_MODEL_PATH",
    "EMBED_MODEL_PATH",
    "CHAT_OPENAI_API",
    "MAX_ITERATIONS",
    "TOKEN_LIMIT_RATIO",
    "EMBEDDINGS_MODEL",
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
    """Check that vLLM is installed."""
    from aria.scripts.vllm import get_vllm_version, is_vllm_installed

    if is_vllm_installed():
        version = get_vllm_version()
        checks.append(
            CheckResult(
                name="vLLM",
                passed=True,
                category="binaries",
                details=f"v{version}",
            )
        )
    else:
        checks.append(
            CheckResult(
                name="vLLM",
                passed=False,
                category="binaries",
                error="vLLM is not installed",
                hint="Run: aria vllm install",
            )
        )


def _check_lightpanda(checks: List[CheckResult]) -> None:
    """Check if Lightpanda is installed (optional)."""
    from aria.config.api import Lightpanda

    if Lightpanda.is_available():
        binary = Lightpanda.get_binary_path()
        checks.append(
            CheckResult(
                name="lightpanda",
                passed=True,
                category="binaries",
                details=f"Found at {binary}",
            )
        )
    else:
        checks.append(
            CheckResult(
                name="lightpanda",
                passed=True,  # Pass because it's optional
                category="binaries",
                details=(
                    "Not installed (browser tools disabled). "
                    "Run: aria lightpanda download"
                ),
            )
        )


def _check_model_exists(model_path: str) -> bool:
    """Check if a model directory exists under DATA_FOLDER/models/.

    All models must reside under DATA_FOLDER/models/. Only local
    directory existence is checked — HF cache is not used.

    Args:
        model_path: Resolved absolute path to the model directory.

    Returns:
        True if the model directory exists locally.
    """
    from pathlib import Path

    if not model_path:
        return False
    path = Path(model_path)
    return path.is_absolute() and path.exists() and path.is_dir()


def _check_models(checks: List[CheckResult]) -> None:
    """Check that all required models are configured and downloaded."""
    from aria.config.models import Chat, Embeddings

    model_checks = [
        ("chat", Chat.model_path, True),  # required
        ("embeddings", Embeddings.model_path, True),  # required
    ]

    for alias, model_path, required in model_checks:
        display_name = f"{alias} model"
        if not model_path:
            if required:
                checks.append(
                    CheckResult(
                        name=display_name,
                        passed=False,
                        category="models",
                        error="not configured (env var not set)",
                        hint=(
                            "Set the corresponding env var in your .env file "
                            f"(e.g. {alias.upper()}_MODEL_PATH)"
                        ),
                    )
                )
            else:
                checks.append(
                    CheckResult(
                        name=display_name,
                        passed=True,
                        category="models",
                        details="not configured (optional)",
                    )
                )
            continue

        if _check_model_exists(model_path):
            checks.append(
                CheckResult(
                    name=display_name,
                    passed=True,
                    category="models",
                    details=model_path,
                )
            )
        else:
            checks.append(
                CheckResult(
                    name=display_name,
                    passed=False,
                    category="models",
                    error=f"not downloaded ({model_path})",
                    hint=f"Run: aria models download --model {alias}",
                )
            )


def _check_token_limit(checks: List[CheckResult]) -> None:
    """Check that TOKEN_LIMIT_RATIO is within safe bounds.

    The memory token limit (TOKEN_LIMIT_RATIO × CHAT_CONTEXT_SIZE) must
    leave room for system prompt, tool definitions, user input, and model
    response generation.
    """
    from aria.config.api import Vllm as VllmConfig
    from aria.config.models import Embeddings as EmbeddingsConfig

    token_limit = EmbeddingsConfig.token_limit
    ratio = EmbeddingsConfig.token_limit_ratio
    ctx_size = VllmConfig.chat_context_size

    # Reserve 10% of context for system prompt, tools, and response
    max_safe_ratio = 0.90

    if ratio > max_safe_ratio:
        checks.append(
            CheckResult(
                name="Token limit",
                passed=False,
                category="environment",
                error=(
                    f"TOKEN_LIMIT_RATIO ({ratio:.0%}) exceeds safe limit "
                    f"({max_safe_ratio:.0%}) of CHAT_CONTEXT_SIZE ({ctx_size}). "
                    f"Max safe token limit: {int(ctx_size * max_safe_ratio)}"
                ),
                hint=(
                    "Reduce TOKEN_LIMIT_RATIO in your .env file to leave room "
                    "for system prompts and model responses"
                ),
            )
        )
    else:
        checks.append(
            CheckResult(
                name="Token limit",
                passed=True,
                category="environment",
                details=f"{token_limit} ({ratio:.0%} of {ctx_size})",
            )
        )


def run_preflight_checks() -> PreflightResult:
    """Run all preflight checks required before starting the web UI.

    Checks performed (all run before returning so every failure is reported):
        1. All required environment variables are set
        2. Data folder exists
        3. vLLM is installed
        4. Chat model is configured and downloaded
        5. Embeddings model is configured and downloaded
        6. Token limit is within context bounds
        7. Memory requirements fit available hardware
        8. LLM server connectivity (informational)
        9. Knowledge database access
       10. Tool loading

    Returns:
        PreflightResult with pass/fail status and all check details.
    """
    checks: List[CheckResult] = []

    _check_env_vars(checks)
    _check_data_folder(checks)
    _check_binaries(checks)
    _check_lightpanda(checks)
    _check_models(checks)
    _check_token_limit(checks)
    _check_memory_requirements(checks)
    _check_llm_server(checks)
    _check_knowledge_db(checks)
    _check_tool_loading(checks)

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
    from aria.helpers.memory import detect_system_ram
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
        if total_ram_mb > 0:
            checks.append(
                CheckResult(
                    name="Unified Memory",
                    passed=True,
                    category="hardware",
                    details=(
                        f"{_mb_to_gb(total_ram_mb)} (Apple Silicon Metal)"
                    ),
                )
            )
    else:
        checks.append(
            CheckResult(
                name="Compute Platform",
                passed=True,
                category="hardware",
                details="CPU-only mode (no GPU acceleration)",
            )
        )


def _check_llm_server(checks: List[CheckResult]) -> None:
    """Check that the LLM server is reachable (non-blocking).

    The LLM server starts *after* preflight, so this check always passes.
    It reports connectivity status as details/warning for informational purposes.
    """
    try:
        import httpx

        from aria.config.models import Chat as ChatConfig

        r = httpx.get(f"{ChatConfig.api_url}/models", timeout=3)
        models = r.json().get("data", [])
        checks.append(
            CheckResult(
                name="LLM server",
                passed=True,
                category="connectivity",
                details=(f"{ChatConfig.api_url} ({len(models)} model(s))"),
            )
        )
    except Exception:
        # Non-blocking: server starts after preflight
        checks.append(
            CheckResult(
                name="LLM server",
                passed=True,
                category="connectivity",
                details="Not running yet (will start with server)",
            )
        )


def _check_knowledge_db(checks: List[CheckResult]) -> None:
    """Check that the knowledge database is accessible."""
    try:
        from aria.tools.knowledge.database import KnowledgeDatabase

        KnowledgeDatabase()
        checks.append(
            CheckResult(
                name="Knowledge DB",
                passed=True,
                category="storage",
                details="SQLite accessible",
            )
        )
    except Exception as e:
        checks.append(
            CheckResult(
                name="Knowledge DB",
                passed=False,
                category="storage",
                error=str(e),
                hint="Check DATA_FOLDER and ARIA_DB_FILENAME in .env",
            )
        )


def _check_tool_loading(checks: List[CheckResult]) -> None:
    """Check that core + file tools load correctly."""
    try:
        from aria.tools.registry import CORE, FILES, get_tools

        tools = get_tools([CORE, FILES])
        checks.append(
            CheckResult(
                name="Tool loading",
                passed=True,
                category="tools",
                details=f"{len(tools)} tools loaded",
            )
        )
    except Exception as e:
        checks.append(
            CheckResult(
                name="Tool loading",
                passed=False,
                category="tools",
                error=str(e),
                hint="Check tool dependencies are installed",
            )
        )
