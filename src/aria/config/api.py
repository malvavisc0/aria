from pathlib import Path
from typing import Optional

from aria.config import get_optional_env
from aria.config.folders import Data


class Vllm:
    """Configuration for the vLLM inference engine.

    All settings are driven by environment variables with sensible defaults.
    Models are loaded directly from HuggingFace Hub (safetensors) — no GGUF
    files or llama.cpp binaries are required.

    ``gpu_memory_utilization`` defaults to ``None``, which triggers
    automatic calculation at server launch time based on detected VRAM,
    model weight size, and a 10 % headroom.  Set the
    ``ARIA_VLLM_GPU_MEMORY_UTILIZATION`` env var to a float (e.g.
    ``0.85``) to override the auto-calculation.
    """

    # --- vLLM engine settings ---
    # None = auto-calculate at launch; set a float to override.
    gpu_memory_utilization: Optional[float] = (
        float(v)
        if (v := get_optional_env("ARIA_VLLM_GPU_MEMORY_UTILIZATION", ""))
        else None
    )
    quantization: Optional[str] = (
        get_optional_env("ARIA_VLLM_QUANT", "") or None
    )
    tensor_parallel_size: int = int(get_optional_env("ARIA_VLLM_TP_SIZE", "1"))
    dtype: str = get_optional_env("ARIA_VLLM_DTYPE", "auto")
    kv_cache_dtype: str = get_optional_env("ARIA_VLLM_KV_CACHE_DTYPE", "auto")
    api_key: str = get_optional_env("ARIA_VLLM_API_KEY", "sk-aria")
    tool_call_parser: str = get_optional_env(
        "ARIA_VLLM_TOOL_CALL_PARSER", "qwen3_coder"
    )
    reasoning_parser: str = get_optional_env(
        "ARIA_VLLM_REASONING_PARSER", "qwen3"
    )

    # Context sizes for each model type
    # Use int(v) if v is non-empty, otherwise fall back to default
    chat_context_size = (
        int(v) if (v := get_optional_env("CHAT_CONTEXT_SIZE", "")) else 65536
    )
    vl_context_size = (
        int(v) if (v := get_optional_env("VL_CONTEXT_SIZE", "")) else 8192
    )
    rerank_context_size = (
        int(v) if (v := get_optional_env("RERANK_CONTEXT_SIZE", "")) else 4096
    )

    # Chat template file (Jinja2) for tool-calling format.
    # Resolved relative to the project root (Path.cwd())
    # Empty string = use model's built-in template.
    _chat_template_raw = get_optional_env("CHAT_TEMPLATE_FILE", "")
    chat_template_file: Optional[Path] = (
        Path.cwd() / Path(_chat_template_raw) if _chat_template_raw else None
    )


class Lightpanda:
    """Configuration for Lightpanda browser binary (optional).

    Lightpanda is a lightweight headless browser that provides CDP
    (Chrome DevTools Protocol) for full browser automation via Playwright.

    Browser tools are disabled if the binary is not installed.
    Run 'aria lightpanda download' to install.
    """

    bin_dir: str = get_optional_env("LIGHTPANDA_BIN_DIR", "bin/lightpanda")
    version: str = get_optional_env("LIGHTPANDA_VERSION", "nightly")
    port: int = int(get_optional_env("LIGHTPANDA_PORT", "9222"))

    @classmethod
    def get_bin_path(cls) -> Path:
        """Get the resolved binary directory path."""
        return Data.path / Path(cls.bin_dir)

    @classmethod
    def get_binary_path(cls) -> Optional[Path]:
        """Get the binary path, or None if not installed.

        Lightpanda uses a single binary name across platforms.

        Returns:
            Path to the binary if it exists, None otherwise.
        """
        bin_path = cls.get_bin_path()
        binary = bin_path / "lightpanda"
        return binary if binary.exists() else None

    @classmethod
    def is_available(cls) -> bool:
        """Check if Lightpanda is installed and ready.

        Returns:
            True if the binary exists, False otherwise.
        """
        return cls.get_binary_path() is not None
