from pathlib import Path
from typing import Optional

from aria.config import get_bool_env, get_optional_env, get_required_env
from aria.config.folders import Data


class LlamaCpp:
    bin_path = Data.path / Path(get_required_env("LLAMA_CPP_BIN_DIR"))
    version = get_required_env("LLAMA_CPP_VERSION")
    models_path = Data.path / Path(get_required_env("GGUF_MODELS_DIR"))

    # Context sizes for each model type
    chat_context_size = int(get_optional_env("CHAT_CONTEXT_SIZE", "65536"))
    vl_context_size = int(get_optional_env("VL_CONTEXT_SIZE", "8192"))
    embeddings_context_size = int(get_optional_env("EMBEDDINGS_CONTEXT_SIZE", "8192"))

    # KV cache location:
    #   True  = offload KV cache to system RAM (slower, saves VRAM)
    #   False = keep KV cache on GPU (faster, uses more VRAM)
    kv_cache_offload = get_bool_env("KV_CACHE_OFFLOAD", True)

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
