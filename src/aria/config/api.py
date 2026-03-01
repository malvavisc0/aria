import os
import platform
from pathlib import Path
from typing import Optional

from aria.config import get_optional_env, get_required_env
from aria.config.folders import Data


class LlamaCpp:
    bin_path = Data.path / Path(get_required_env("LLAMA_CPP_BIN_DIR"))
    version = get_required_env("LLAMA_CPP_VERSION")
    models_path = Data.path / Path(get_required_env("GGUF_MODELS_DIR"))

    # Context sizes for each model type
    chat_context_size = int(get_optional_env("CHAT_CONTEXT_SIZE", "65536"))
    vl_context_size = int(get_optional_env("VL_CONTEXT_SIZE", "8192"))
    embeddings_context_size = int(get_optional_env("EMBEDDINGS_CONTEXT_SIZE", "8192"))


class AgentBrowser:
    """Configuration for agent-browser binary (optional).

    Agent-browser is a Rust CLI binary for headless browser automation
    designed for AI agents. It provides anti-bot bypass by using an
    actual Chromium browser via Playwright.

    Browser tools are disabled if the binary is not installed.
    Run 'aria agentbrowser download' to install.
    """

    # Use get_optional_env since browser tools are optional
    bin_dir: str = get_optional_env("AGENT_BROWSER_BIN_DIR", "bin/agentbrowser")
    version: str = get_optional_env("AGENT_BROWSER_VERSION", "latest")

    @classmethod
    def get_bin_path(cls) -> Path:
        """Get the resolved binary directory path."""
        return Data.path / Path(cls.bin_dir)

    @classmethod
    def get_binary_path(cls) -> Optional[Path]:
        """Get the platform-specific binary path, or None if not installed.

        Returns:
            Path to the binary if it exists, None otherwise.
        """
        bin_path = cls.get_bin_path()

        # Map platform to binary name
        system = platform.system().lower()
        machine = platform.machine().lower()

        if system == "linux":
            arch = "arm64" if "aarch64" in machine else "x64"
            name = f"agent-browser-linux-{arch}"
        elif system == "darwin":
            arch = "arm64" if "arm" in machine else "x64"
            name = f"agent-browser-darwin-{arch}"
        elif system == "windows":
            name = "agent-browser-win32-x64.exe"
        else:
            return None

        binary = bin_path / name
        return binary if binary.exists() else None

    @classmethod
    def is_available(cls) -> bool:
        """Check if agent-browser is installed and ready.

        Returns:
            True if the binary exists, False otherwise.
        """
        return cls.get_binary_path() is not None

    @classmethod
    def get_env(cls) -> dict[str, str]:
        """Return an environment dict with ``AGENT_BROWSER_HOME`` set.

        The agent-browser binary requires this variable to locate its
        daemon and Chromium installation.  The value is the resolved
        binary directory (``get_bin_path()``).

        Returns:
            A copy of ``os.environ`` with ``AGENT_BROWSER_HOME`` added.
        """
        return {**os.environ, "AGENT_BROWSER_HOME": str(cls.get_bin_path())}
