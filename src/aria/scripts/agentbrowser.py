"""Download and manage agent-browser binaries from GitHub releases.

This module provides functionality to download and manage agent-browser
binaries from the Vercel Labs GitHub releases. Agent-browser is a Rust CLI
for headless browser automation designed for AI agents.

Example:
    ```python
    from pathlib import Path
    from aria.scripts.agentbrowser import download_agent_browser

    # Download the latest release to bin/agentbrowser/
    download_agent_browser(bin_dir=Path("bin/agentbrowser"))
    ```
"""

import json
import platform
import stat
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

from loguru import logger
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

console = Console(width=200)
error_console = Console(stderr=True, style="bold red", width=200)

# GitHub repository for agent-browser
GITHUB_REPO = "vercel-labs/agent-browser"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def download_agent_browser(bin_dir: Path, version: Optional[str] = None) -> Path:
    """Download agent-browser binary for current platform.

    Args:
        bin_dir: Directory to install the binary to.
        version: Specific version tag (default: latest).

    Returns:
        Path to the downloaded binary.

    Raises:
        RuntimeError: If download or installation fails.

    Steps:
        1. Fetch release info from GitHub API
        2. Find platform-specific asset
        3. Download binary
        4. Make executable (chmod +x)
        5. Run `agent-browser install` to download Chromium
           (system dependencies must be installed manually if needed)
    """
    bin_dir = Path(bin_dir)
    bin_dir.mkdir(parents=True, exist_ok=True)

    # Get release info
    if version and version != "latest":
        release_info = _get_release_by_tag(version)
    else:
        release_info = _get_latest_release_info()

    tag_name = release_info.get("tag_name", "unknown")
    logger.info(f"Downloading agent-browser {tag_name}")

    # Find platform-specific asset
    asset = _find_platform_asset(release_info.get("assets", []))
    if not asset:
        raise RuntimeError(
            f"No agent-browser binary found for platform: "
            f"{platform.system()}-{platform.machine()}"
        )

    download_url = asset["browser_download_url"]
    binary_name = asset["name"]
    binary_path = bin_dir / binary_name

    # Download the binary
    console.print(f"[cyan]Downloading[/cyan] {binary_name}...")
    _download_file(download_url, binary_path)

    # Make executable on Unix
    if platform.system() != "Windows":
        current_mode = binary_path.stat().st_mode
        binary_path.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    console.print(f"[green]✓[/green] Downloaded to {binary_path}")

    # Install Chromium
    install_chromium(binary_path)

    return binary_path


def get_agent_browser_binary(bin_dir: Optional[Path] = None) -> Optional[Path]:
    """Find the agent-browser binary in the given directory.

    Args:
        bin_dir: Directory to search. If None, uses default config.

    Returns:
        Path to the binary if found, None otherwise.
    """
    if bin_dir is None:
        from aria.config.api import AgentBrowser

        bin_dir = AgentBrowser.get_bin_path()

    bin_dir = Path(bin_dir)
    if not bin_dir.exists():
        return None

    # Find the platform-specific binary name
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

    binary = bin_dir / name
    return binary if binary.exists() else None


def install_chromium(binary_path: Path) -> None:
    """Run agent-browser install to download Chromium.

    This downloads Chromium for agent-browser to use for browser automation.
    On Linux, it may require system dependencies - if installation fails,
    you may need to install them manually.

    Args:
        binary_path: Path to the agent-browser binary.

    Raises:
        RuntimeError: If Chromium installation fails.
    """
    console.print("[cyan]Installing Chromium[/cyan] (this may take a moment)...")

    # Run agent-browser install without --with-deps
    # This downloads Chromium without trying to install system dependencies
    from aria.config.api import AgentBrowser

    cmd = [str(binary_path), "install"]
    env = AgentBrowser.get_env()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes for Chromium download
            env=env,
        )

        if result.returncode == 0:
            console.print("[green]✓[/green] Chromium installed successfully")
            return

        error_msg = result.stderr or result.stdout or ""

        # Provide helpful error message instead of trying sudo
        console.print("[yellow]⚠[/yellow] Chromium installation encountered an issue.")
        console.print(
            "[yellow]⚠[/yellow] This may be due to missing system " "dependencies."
        )
        console.print("[yellow]⚠[/yellow] You may need to install them manually.")
        console.print(f"\n[yellow]Error details:[/yellow]\n{error_msg}\n")
        console.print("[yellow]To install dependencies manually on Linux:[/yellow]")
        console.print(
            "  Ubuntu/Debian: sudo apt-get install -y "
            "libnss3 libnspr4 libdbus-1-3 "
            "libxshmfence1 libasound2 libatk1.0-0 libatk-bridge2.0-0 "
            "libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 "
            "libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 "
            "libatspi2.0-0"
        )
        console.print(
            "  Fedora: sudo dnf install -y "
            "nss nspr dbus-libs libXshmfence alsa-lib "
            "atk at-spi2-atk cups-libs libdrm libxkbcommon "
            "libXcomposite libXdamage libXfixes libXrandr mesa-libgbm "
            "pango cairo at-spi2-core"
        )
        console.print(
            "  Arch Linux: sudo pacman -S "
            "nss dbus libxshmfence alsa-lib "
            "atk at-spi2-atk libcups libdrm libxkbcommon "
            "libxcomposite libxdamage libxfixes libxrandr "
            "mesa pango cairo at-spi2-core"
        )
        raise RuntimeError(f"Chromium installation failed: {error_msg}")

    except subprocess.TimeoutExpired:
        raise RuntimeError("Chromium installation timed out after 5 minutes")
    except Exception as e:
        raise RuntimeError(f"Chromium installation failed: {e}")


def _get_latest_release_info() -> dict:
    """Fetch the latest release information from GitHub API.

    Returns:
        dict: Release information including tag_name and assets.

    Raises:
        RuntimeError: If the API request fails.
    """
    try:
        req = urllib.request.Request(
            GITHUB_API_URL,
            headers={"Accept": "application/vnd.github.v3+json"},
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"GitHub API error: {e.code} {e.reason}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error: {e.reason}")


def _get_release_by_tag(tag: str) -> dict:
    """Fetch release information for a specific tag.

    Args:
        tag: The release tag (e.g., "v1.0.0").

    Returns:
        dict: Release information including tag_name and assets.

    Raises:
        RuntimeError: If the API request fails.
    """
    url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/tags/{tag}"
    try:
        req = urllib.request.Request(
            url,
            headers={"Accept": "application/vnd.github.v3+json"},
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise RuntimeError(f"Release not found: {tag}")
        raise RuntimeError(f"GitHub API error: {e.code} {e.reason}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error: {e.reason}")


def _find_platform_asset(assets: list) -> Optional[dict]:
    """Find the correct asset for current platform.

    Maps platform.system() and platform.machine() to asset names:
    - Linux x64 -> agent-browser-linux-x64
    - Linux ARM64 -> agent-browser-linux-arm64
    - macOS ARM -> agent-browser-darwin-arm64
    - macOS x64 -> agent-browser-darwin-x64
    - Windows x64 -> agent-browser-win32-x64.exe

    Args:
        assets: List of asset dictionaries from GitHub release.

    Returns:
        The matching asset dict, or None if not found.
    """
    system = platform.system().lower()
    machine = platform.machine().lower()

    # Determine the expected binary name
    if system == "linux":
        arch = "arm64" if "aarch64" in machine else "x64"
        expected_name = f"agent-browser-linux-{arch}"
    elif system == "darwin":
        arch = "arm64" if "arm" in machine else "x64"
        expected_name = f"agent-browser-darwin-{arch}"
    elif system == "windows":
        expected_name = "agent-browser-win32-x64.exe"
    else:
        logger.warning(f"Unsupported platform: {system}")
        return None

    # Find matching asset
    for asset in assets:
        if asset.get("name") == expected_name:
            return asset

    logger.warning(f"No asset found matching: {expected_name}")
    return None


def _download_file(url: str, dest: Path) -> None:
    """Download a file with progress bar.

    Args:
        url: The URL to download from.
        dest: The destination file path.
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Downloading", total=None)

        # Get file size
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=30) as response:
            total_size = int(response.headers.get("content-length", 0))

        progress.update(task, total=total_size)

        # Download with progress
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=300) as response:
            with open(dest, "wb") as f:
                downloaded = 0
                chunk_size = 8192
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    progress.update(task, completed=downloaded)
