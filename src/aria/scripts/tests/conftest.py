"""Shared fixtures and utilities for llama.py tests."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# ============================================================================
# Mock Data Constants
# ============================================================================

MOCK_GITHUB_RELEASE_LATEST = {
    "tag_name": "v1.2.3",
    "assets": [
        {
            "name": "ubuntu-x64.tar.gz",
            "browser_download_url": "https://example.com/ubuntu-x64.tar.gz",
        },
        {
            "name": "linux-gpu.tar.gz",
            "browser_download_url": "https://example.com/linux-gpu.tar.gz",
        },
        {
            "name": "README.md",
            "browser_download_url": "https://example.com/README.md",
        },
    ],
}

MOCK_GITHUB_RELEASE_WITH_CUDA = {
    "tag_name": "v1.2.3",
    "assets": [
        {
            "name": "linux-gpu-cuda.tar.gz",
            "browser_download_url": "https://example.com/linux-gpu-cuda.tar.gz",
        },
    ],
}

MOCK_GITHUB_RELEASE_NO_LINUX = {
    "tag_name": "v1.2.3",
    "assets": [
        {
            "name": "macos-x64.zip",
            "browser_download_url": "https://example.com/macos-x64.zip",
        },
        {
            "name": "windows-x64.zip",
            "browser_download_url": "https://example.com/windows-x64.zip",
        },
    ],
}

MOCK_GITHUB_RELEASE_EMPTY = {
    "tag_name": "v1.2.3",
    "assets": [],
}

MOCK_NVIDIA_SMI_GPU_LIST = "GPU 0: NVIDIA GeForce RTX 3090 (UUID: GPU-xxx)"

MOCK_NVIDIA_SMI_VERSION = (
    "NVIDIA-SMI 535.104.05    Driver Version: 535.104.05    CUDA Version: 12.2"
)

MOCK_OS_RELEASE_UBUNTU = """NAME="Ubuntu"
VERSION="22.04.3 LTS (Jammy Jellyfish)"
ID=ubuntu
ID_LIKE=debian
PRETTY_NAME="Ubuntu 22.04.3 LTS"
VERSION_ID="22.04"
"""

MOCK_OS_RELEASE_DEBIAN = """PRETTY_NAME="Debian GNU/Linux 12 (bookworm)"
NAME="Debian GNU/Linux"
VERSION_ID="12"
"""

MOCK_OS_RELEASE_FEDORA = """NAME="Fedora Linux"
VERSION="39 (Workstation Edition)"
ID=fedora
"""

# ============================================================================
# Platform Fixtures
# ============================================================================


@pytest.fixture
def mock_platform_linux():
    """Mock platform.system() to return 'Linux'."""
    with patch("platform.system", return_value="Linux"):
        yield


@pytest.fixture
def mock_platform_windows():
    """Mock platform.system() to return 'Windows'."""
    with patch("platform.system", return_value="Windows"):
        yield


@pytest.fixture
def mock_platform_macos():
    """Mock platform.system() to return 'Darwin' (macOS)."""
    with patch("platform.system", return_value="Darwin"):
        yield


# ============================================================================
# OS Release Fixtures
# ============================================================================


@pytest.fixture
def mock_os_release_ubuntu(mock_platform_linux):
    """Mock /etc/os-release for Ubuntu."""
    with patch("builtins.open") as mock_open:
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = MOCK_OS_RELEASE_UBUNTU
        mock_open.return_value = mock_file
        yield


@pytest.fixture
def mock_os_release_debian(mock_platform_linux):
    """Mock /etc/os-release for Debian."""
    with patch("builtins.open") as mock_open:
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = MOCK_OS_RELEASE_DEBIAN
        mock_open.return_value = mock_file
        yield


@pytest.fixture
def mock_os_release_fedora(mock_platform_linux):
    """Mock /etc/os-release for Fedora."""
    with patch("builtins.open") as mock_open:
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = MOCK_OS_RELEASE_FEDORA
        mock_open.return_value = mock_file
        yield


@pytest.fixture
def mock_os_release_missing(mock_platform_linux):
    """Mock missing /etc/os-release file."""
    with patch("builtins.open") as mock_open:
        mock_open.side_effect = FileNotFoundError("/etc/os-release not found")
        yield


# ============================================================================
# Subprocess Fixtures
# ============================================================================


@pytest.fixture
def mock_subprocess_success():
    """Create a mock for successful subprocess.run calls."""

    def _mock_run(cmd, **kwargs):
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        return mock_result

    with patch("subprocess.run", side_effect=_mock_run):
        yield


@pytest.fixture
def mock_subprocess_failure():
    """Create a mock that raises CalledProcessError."""

    def _mock_run(cmd, **kwargs):
        raise subprocess.CalledProcessError(1, cmd, "Error")

    with patch("subprocess.run", side_effect=_mock_run):
        yield


@pytest.fixture
def mock_subprocess_not_found():
    """Create a mock that raises FileNotFoundError."""

    def _mock_run(cmd, **kwargs):
        raise FileNotFoundError(f"{cmd[0]} not found")

    with patch("subprocess.run", side_effect=_mock_run):
        yield


# ============================================================================
# NVIDIA/SMI Fixtures
# ============================================================================


@pytest.fixture
def mock_nvidia_smi_available():
    """Mock nvidia-smi as available."""
    with patch("aria.nvidia.check_nvidia_smi_available", return_value=True):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=MOCK_NVIDIA_SMI_GPU_LIST)
            yield


@pytest.fixture
def mock_nvidia_smi_unavailable():
    """Mock nvidia-smi as unavailable."""
    with patch("aria.nvidia.check_nvidia_smi_available", return_value=False):
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("nvidia-smi not found")
            yield


# ============================================================================
# GitHub API Fixtures
# ============================================================================


@pytest.fixture
def mock_github_api_latest(mock_platform_linux):
    """Mock GitHub API for latest release."""
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = (
            __import__("json").dumps(MOCK_GITHUB_RELEASE_LATEST).encode()
        )
        mock_urlopen.return_value.__enter__.return_value = mock_response
        yield


@pytest.fixture
def mock_github_api_by_tag(mock_platform_linux):
    """Mock GitHub API for specific tag."""
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = (
            __import__("json").dumps(MOCK_GITHUB_RELEASE_LATEST).encode()
        )
        mock_urlopen.return_value.__enter__.return_value = mock_response
        yield


@pytest.fixture
def mock_github_api_no_linux(mock_platform_linux):
    """Mock GitHub API with no Linux assets."""
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = (
            __import__("json").dumps(MOCK_GITHUB_RELEASE_NO_LINUX).encode()
        )
        mock_urlopen.return_value.__enter__.return_value = mock_response
        yield


# ============================================================================
# File System Fixtures
# ============================================================================


@pytest.fixture
def temp_bin_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for binary installation."""
    return tmp_path / "bin" / "llamacpp"


@pytest.fixture
def mock_temp_dir(tmp_path: Path):
    """Mock tempfile.TemporaryDirectory to use tmp_path."""
    with patch("tempfile.TemporaryDirectory") as mock_tempdir:
        mock_tempdir.return_value.__enter__.return_value = str(tmp_path / "tmp")
        mock_tempdir.return_value.__exit__.return_value = None
        yield tmp_path / "tmp"


# ============================================================================
# Console Fixtures
# ============================================================================


@pytest.fixture
def mock_console():
    """Mock rich.Console to suppress output during tests."""
    with patch("aria.scripts.llama.console") as mock_console:
        with patch("aria.scripts.llama.error_console"):
            yield mock_console


# ============================================================================
# nvcc Fixtures
# ============================================================================


@pytest.fixture
def mock_nvcc_available():
    """Mock nvcc as available."""
    with patch("subprocess.run") as mock_run:
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "/usr/bin/nvcc"
        mock_run.return_value = mock_result
        yield


@pytest.fixture
def mock_nvcc_unavailable():
    """Mock nvcc as unavailable."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError("which: no nvcc in PATH")
        yield
