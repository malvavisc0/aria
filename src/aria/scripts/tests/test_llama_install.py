"""Tests for installation functions in llama.py."""

import subprocess
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from aria.scripts.llama import BINARY_NAMES, download_llama_cpp


class TestDownloadLatestLlamaCppNonLinux:
    """Tests for download_llama_cpp() on non-Linux systems."""

    def test_raises_not_implemented_on_windows(self, tmp_path: Path):
        """Test that download_llama_cpp raises NotImplementedError on Windows."""
        with patch("platform.system", return_value="Windows"):
            with pytest.raises(NotImplementedError) as exc_info:
                download_llama_cpp(bin_dir=tmp_path)

            assert "Source compilation is required" in str(exc_info.value)
            assert "non-Linux systems" in str(exc_info.value)

    def test_raises_not_implemented_on_macos(self, tmp_path: Path):
        """Test that download_llama_cpp raises NotImplementedError on macOS."""
        with patch("platform.system", return_value="Darwin"):
            with pytest.raises(NotImplementedError) as exc_info:
                download_llama_cpp(bin_dir=tmp_path)

            assert "Source compilation is required" in str(exc_info.value)


class TestDownloadLatestLlamaCppUbuntuNoNvcc:
    """Tests for download_llama_cpp() on Ubuntu without nvcc."""

    def test_downloads_prebuilt_binary_success(self, tmp_path: Path):
        """Test that download_llama_cpp downloads pre-built binary on Ubuntu without CUDA."""
        with (
            patch("platform.system", return_value="Linux"),
            patch("builtins.open") as mock_open,
            patch("aria.scripts.llama._nvcc_available", return_value=False),
            patch("aria.scripts.llama._get_latest_release_info") as mock_release,
            patch("aria.scripts.llama._download_and_extract") as mock_extract,
            patch("aria.scripts.llama.get_llama_cpp_binary") as mock_get_binary,
            patch("aria.scripts.llama._make_executable"),
        ):
            # Mock Ubuntu OS release
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = """
NAME="Ubuntu"
VERSION="22.04.3 LTS (Jammy Jellyfish)"
ID=ubuntu
ID_LIKE=debian
PRETTY_NAME="Ubuntu 22.04.3 LTS"
VERSION_ID="22.04"
"""
            mock_open.return_value = mock_file

            # Mock release info
            mock_release.return_value = {
                "tag_name": "v1.2.3",
                "assets": [
                    {
                        "name": "ubuntu-x64.tar.gz",
                        "browser_download_url": "https://example.com/ubuntu-x64.tar.gz",
                    }
                ],
            }

            # Mock extract
            mock_extract.return_value = [str(tmp_path / "llama-cli")]

            # Mock get_llama_cpp_binary
            mock_get_binary.return_value = tmp_path / "llama-cli"

            result = download_llama_cpp(bin_dir=tmp_path)

            assert result == tmp_path
            mock_extract.assert_called_once()

    def test_raises_error_when_no_linux_binary(self, tmp_path: Path):
        """Test that download_llama_cpp raises error when no Linux binary found."""
        with (
            patch("platform.system", return_value="Linux"),
            patch("builtins.open") as mock_open,
            patch("aria.scripts.llama._nvcc_available", return_value=False),
            patch("aria.scripts.llama._get_latest_release_info") as mock_release,
        ):
            # Mock Ubuntu OS release
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = """
NAME="Ubuntu"
VERSION="22.04.3 LTS (Jammy Jellyfish)"
ID=ubuntu
"""
            mock_open.return_value = mock_file

            # Mock release info with no Linux assets
            mock_release.return_value = {
                "tag_name": "v1.2.3",
                "assets": [
                    {
                        "name": "macos-x64.zip",
                        "browser_download_url": "https://example.com/macos-x64.zip",
                    }
                ],
            }

            with pytest.raises(RuntimeError) as exc_info:
                download_llama_cpp(bin_dir=tmp_path)

            assert "No suitable Linux binary found" in str(exc_info.value)

    def test_raises_error_when_no_download_url(self, tmp_path: Path):
        """Test that download_llama_cpp raises error when no download URL."""
        with (
            patch("platform.system", return_value="Linux"),
            patch("builtins.open") as mock_open,
            patch("aria.scripts.llama._nvcc_available", return_value=False),
            patch("aria.scripts.llama._get_latest_release_info") as mock_release,
        ):
            # Mock Ubuntu OS release
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = """
NAME="Ubuntu"
VERSION="22.04.3 LTS (Jammy Jellyfish)"
ID=ubuntu
"""
            mock_open.return_value = mock_file

            # Mock release info without download URL
            mock_release.return_value = {
                "tag_name": "v1.2.3",
                "assets": [{"name": "ubuntu-x64.tar.gz"}],
            }

            with pytest.raises(RuntimeError) as exc_info:
                download_llama_cpp(bin_dir=tmp_path)

            assert "Could not find download URL" in str(exc_info.value)

    def test_handles_network_error(self, tmp_path: Path):
        """Test that download_llama_cpp handles network errors."""
        with (
            patch("platform.system", return_value="Linux"),
            patch("builtins.open") as mock_open,
            patch("aria.scripts.llama._nvcc_available", return_value=False),
            patch("aria.scripts.llama._get_latest_release_info") as mock_release,
        ):
            # Mock Ubuntu OS release
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = """
NAME="Ubuntu"
VERSION="22.04.3 LTS (Jammy Jellyfish)"
ID=ubuntu
"""
            mock_open.return_value = mock_file

            # Mock network error
            mock_release.side_effect = urllib.error.URLError("Network error")

            with pytest.raises(urllib.error.URLError):
                download_llama_cpp(bin_dir=tmp_path)


class TestDownloadLatestLlamaCppUbuntuWithNvcc:
    """Tests for download_llama_cpp() on Ubuntu with nvcc (CUDA)."""

    def test_compiles_from_source_with_cuda(self, tmp_path: Path):
        """Test that download_llama_cpp compiles from source with CUDA on Ubuntu with nvcc."""
        with (
            patch("platform.system", return_value="Linux"),
            patch("builtins.open") as mock_open,
            patch("aria.scripts.llama._nvcc_available", return_value=True),
            patch("aria.scripts.llama._get_latest_release_info") as mock_release,
            patch("aria.scripts.llama._download_and_extract_zip") as mock_extract_zip,
            patch("aria.scripts.llama.install_llama_cpp_from_source") as mock_compile,
            patch("aria.scripts.llama.get_llama_cpp_binary") as mock_get_binary,
            patch("aria.scripts.llama._make_executable"),
            patch("subprocess.run") as mock_run,
        ):
            # Mock Ubuntu OS release
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = """
NAME="Ubuntu"
VERSION="22.04.3 LTS (Jammy Jellyfish)"
ID=ubuntu
"""
            mock_open.return_value = mock_file

            # Mock release info
            mock_release.return_value = {
                "tag_name": "v1.2.3",
                "assets": [
                    {
                        "name": "ubuntu-x64.tar.gz",
                        "browser_download_url": "https://example.com/ubuntu-x64.tar.gz",
                    }
                ],
            }

            # Mock extract_zip
            mock_extract_zip.return_value = tmp_path / "source" / "llama.cpp-v1.2.3"

            # Mock compile
            mock_compile.return_value = tmp_path / "build"

            # Mock get_llama_cpp_binary
            mock_get_binary.return_value = tmp_path / "llama-server"

            # Mock subprocess.run
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "llama-server version: v1.2.3"
            mock_run.return_value = mock_result

            result = download_llama_cpp(bin_dir=tmp_path)

            assert result == tmp_path
            mock_compile.assert_called_once()
            # Verify CUDA is enabled
            call_kwargs = mock_compile.call_args.kwargs
            assert call_kwargs["use_cuda"] is True
            assert call_kwargs["use_blas"] is True


class TestDownloadLatestLlamaCppNonUbuntuLinux:
    """Tests for download_llama_cpp() on non-Ubuntu Linux."""

    def test_compiles_from_source_without_cuda(self, tmp_path: Path):
        """Test that download_llama_cpp compiles from source without CUDA on non-Ubuntu Linux."""
        with (
            patch("platform.system", return_value="Linux"),
            patch("builtins.open") as mock_open,
            patch("aria.scripts.llama._nvcc_available", return_value=False),
            patch("aria.scripts.llama._is_ubuntu", return_value=False),
            patch("aria.scripts.llama._get_latest_release_info") as mock_release,
            patch("aria.scripts.llama._download_and_extract_zip") as mock_extract_zip,
            patch("aria.scripts.llama.install_llama_cpp_from_source") as mock_compile,
            patch("aria.scripts.llama.get_llama_cpp_binary") as mock_get_binary,
            patch("aria.scripts.llama._make_executable"),
            patch("subprocess.run") as mock_run,
        ):
            # Mock Debian OS release
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = """
PRETTY_NAME="Debian GNU/Linux 12 (bookworm)"
NAME="Debian GNU/Linux"
VERSION_ID="12"
"""
            mock_open.return_value = mock_file

            # Mock release info
            mock_release.return_value = {
                "tag_name": "v1.2.3",
                "assets": [
                    {
                        "name": "linux.tar.gz",
                        "browser_download_url": "https://example.com/linux.tar.gz",
                    }
                ],
            }

            # Mock extract_zip
            mock_extract_zip.return_value = tmp_path / "source" / "llama.cpp-v1.2.3"

            # Mock compile
            mock_compile.return_value = tmp_path / "build"

            # Mock get_llama_cpp_binary
            mock_get_binary.return_value = tmp_path / "llama-server"

            # Mock subprocess.run
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "llama-server version: v1.2.3"
            mock_run.return_value = mock_result

            result = download_llama_cpp(bin_dir=tmp_path)

            assert result == tmp_path
            mock_compile.assert_called_once()
            # Verify CUDA is disabled when nvcc not available
            call_kwargs = mock_compile.call_args.kwargs
            assert call_kwargs["use_cuda"] is False
            assert call_kwargs["use_blas"] is False

    def test_compiles_from_source_with_cuda_when_nvcc_available(self, tmp_path: Path):
        """Test that download_llama_cpp compiles from source with CUDA when nvcc is available."""
        with (
            patch("platform.system", return_value="Linux"),
            patch("builtins.open") as mock_open,
            patch("aria.scripts.llama._nvcc_available", return_value=True),
            patch("aria.scripts.llama._is_ubuntu", return_value=False),
            patch("aria.scripts.llama._get_latest_release_info") as mock_release,
            patch("aria.scripts.llama._download_and_extract_zip") as mock_extract_zip,
            patch("aria.scripts.llama.install_llama_cpp_from_source") as mock_compile,
            patch("aria.scripts.llama.get_llama_cpp_binary") as mock_get_binary,
            patch("aria.scripts.llama._make_executable"),
            patch("subprocess.run") as mock_run,
        ):
            # Mock Debian OS release
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = """
PRETTY_NAME="Debian GNU/Linux 12 (bookworm)"
NAME="Debian GNU/Linux"
VERSION_ID="12"
"""
            mock_open.return_value = mock_file

            # Mock release info
            mock_release.return_value = {
                "tag_name": "v1.2.3",
                "assets": [
                    {
                        "name": "linux.tar.gz",
                        "browser_download_url": "https://example.com/linux.tar.gz",
                    }
                ],
            }

            # Mock extract_zip
            mock_extract_zip.return_value = tmp_path / "source" / "llama.cpp-v1.2.3"

            # Mock compile
            mock_compile.return_value = tmp_path / "build"

            # Mock get_llama_cpp_binary
            mock_get_binary.return_value = tmp_path / "llama-server"

            # Mock subprocess.run
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "llama-server version: v1.2.3"
            mock_run.return_value = mock_result

            result = download_llama_cpp(bin_dir=tmp_path)

            assert result == tmp_path
            mock_compile.assert_called_once()
            # Verify CUDA and BLAS are enabled when nvcc available
            call_kwargs = mock_compile.call_args.kwargs
            assert call_kwargs["use_cuda"] is True
            assert call_kwargs["use_blas"] is True


class TestDownloadLatestLlamaCppVersionParameter:
    """Tests for download_llama_cpp() with version parameter."""

    def test_downloads_specific_version(self, tmp_path: Path):
        """Test that download_llama_cpp downloads specific version when version is provided."""
        with (
            patch("platform.system", return_value="Linux"),
            patch("builtins.open") as mock_open,
            patch("aria.scripts.llama._nvcc_available", return_value=False),
            patch("aria.scripts.llama._get_release_by_tag") as mock_release,
            patch("aria.scripts.llama._download_and_extract") as mock_extract,
            patch("aria.scripts.llama.get_llama_cpp_binary") as mock_get_binary,
            patch("aria.scripts.llama._make_executable"),
        ):
            # Mock Ubuntu OS release
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = """
NAME="Ubuntu"
VERSION="22.04.3 LTS (Jammy Jellyfish)"
ID=ubuntu
"""
            mock_open.return_value = mock_file

            # Mock release info
            mock_release.return_value = {
                "tag_name": "v1.2.3",
                "assets": [
                    {
                        "name": "ubuntu-x64.tar.gz",
                        "browser_download_url": "https://example.com/ubuntu-x64.tar.gz",
                    }
                ],
            }

            # Mock extract
            mock_extract.return_value = [str(tmp_path / "llama-cli")]

            # Mock get_llama_cpp_binary
            mock_get_binary.return_value = tmp_path / "llama-cli"

            result = download_llama_cpp(bin_dir=tmp_path, version="v1.2.3")

            assert result == tmp_path

    def test_downloads_latest_when_version_is_latest(self, tmp_path: Path):
        """Test that download_llama_cpp downloads latest when version is 'latest'."""
        with (
            patch("platform.system", return_value="Linux"),
            patch("builtins.open") as mock_open,
            patch("aria.scripts.llama._nvcc_available", return_value=False),
            patch("aria.scripts.llama._get_latest_release_info") as mock_release,
            patch("aria.scripts.llama._download_and_extract") as mock_extract,
            patch("aria.scripts.llama.get_llama_cpp_binary") as mock_get_binary,
            patch("aria.scripts.llama._make_executable"),
        ):
            # Mock Ubuntu OS release
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = """
NAME="Ubuntu"
VERSION="22.04.3 LTS (Jammy Jellyfish)"
ID=ubuntu
"""
            mock_open.return_value = mock_file

            # Mock release info
            mock_release.return_value = {
                "tag_name": "v1.2.3",
                "assets": [
                    {
                        "name": "ubuntu-x64.tar.gz",
                        "browser_download_url": "https://example.com/ubuntu-x64.tar.gz",
                    }
                ],
            }

            # Mock extract
            mock_extract.return_value = [str(tmp_path / "llama-cli")]

            # Mock get_llama_cpp_binary
            mock_get_binary.return_value = tmp_path / "llama-cli"

            result = download_llama_cpp(bin_dir=tmp_path, version="latest")

            assert result == tmp_path


class TestDownloadLatestLlamaCppBinaryTesting:
    """Tests for binary testing in download_llama_cpp()."""

    def test_tests_binary_after_installation(self, tmp_path: Path):
        """Test that download_llama_cpp tests binary after installation."""
        with (
            patch("platform.system", return_value="Linux"),
            patch("builtins.open") as mock_open,
            patch("aria.scripts.llama._nvcc_available", return_value=False),
            patch("aria.scripts.llama._get_latest_release_info") as mock_release,
            patch("aria.scripts.llama._download_and_extract") as mock_extract,
            patch("aria.scripts.llama.get_llama_cpp_binary") as mock_get_binary,
            patch("aria.scripts.llama._make_executable"),
            patch("subprocess.run") as mock_run,
        ):
            # Mock Ubuntu OS release
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = """
NAME="Ubuntu"
VERSION="22.04.3 LTS (Jammy Jellyfish)"
ID=ubuntu
"""
            mock_open.return_value = mock_file

            # Mock release info
            mock_release.return_value = {
                "tag_name": "v1.2.3",
                "assets": [
                    {
                        "name": "ubuntu-x64.tar.gz",
                        "browser_download_url": "https://example.com/ubuntu-x64.tar.gz",
                    }
                ],
            }

            # Mock extract
            mock_extract.return_value = [str(tmp_path / "llama-cli")]

            # Mock get_llama_cpp_binary
            mock_get_binary.return_value = tmp_path / "llama-cli"

            # Mock subprocess.run (not used in Ubuntu pre-built binary path)
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "llama-server version: v1.2.3"
            mock_run.return_value = mock_result

            result = download_llama_cpp(bin_dir=tmp_path)

            assert result == tmp_path
            # Binary testing is not performed for Ubuntu pre-built binaries
            # It's only done when compiling from source
            mock_run.assert_not_called()

    def test_handles_binary_test_timeout(self, tmp_path: Path):
        """Test that download_llama_cpp handles binary test timeout."""
        with (
            patch("platform.system", return_value="Linux"),
            patch("builtins.open") as mock_open,
            patch("aria.scripts.llama._nvcc_available", return_value=False),
            patch("aria.scripts.llama._get_latest_release_info") as mock_release,
            patch("aria.scripts.llama._download_and_extract") as mock_extract,
            patch("aria.scripts.llama.get_llama_cpp_binary") as mock_get_binary,
            patch("aria.scripts.llama._make_executable"),
            patch("subprocess.run") as mock_run,
        ):
            # Mock Ubuntu OS release
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = """
NAME="Ubuntu"
VERSION="22.04.3 LTS (Jammy Jellyfish)"
ID=ubuntu
"""
            mock_open.return_value = mock_file

            # Mock release info
            mock_release.return_value = {
                "tag_name": "v1.2.3",
                "assets": [
                    {
                        "name": "ubuntu-x64.tar.gz",
                        "browser_download_url": "https://example.com/ubuntu-x64.tar.gz",
                    }
                ],
            }

            # Mock extract
            mock_extract.return_value = [str(tmp_path / "llama-cli")]

            # Mock get_llama_cpp_binary
            mock_get_binary.return_value = tmp_path / "llama-cli"

            # Mock subprocess.run to raise TimeoutExpired
            mock_run.side_effect = subprocess.TimeoutExpired("llama-server", 10)

            result = download_llama_cpp(bin_dir=tmp_path)

            assert result == tmp_path

    def test_handles_binary_test_failure(self, tmp_path: Path):
        """Test that download_llama_cpp handles binary test failure."""
        with (
            patch("platform.system", return_value="Linux"),
            patch("builtins.open") as mock_open,
            patch("aria.scripts.llama._nvcc_available", return_value=False),
            patch("aria.scripts.llama._get_latest_release_info") as mock_release,
            patch("aria.scripts.llama._download_and_extract") as mock_extract,
            patch("aria.scripts.llama.get_llama_cpp_binary") as mock_get_binary,
            patch("aria.scripts.llama._make_executable"),
            patch("subprocess.run") as mock_run,
        ):
            # Mock Ubuntu OS release
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = """
NAME="Ubuntu"
VERSION="22.04.3 LTS (Jammy Jellyfish)"
ID=ubuntu
"""
            mock_open.return_value = mock_file

            # Mock release info
            mock_release.return_value = {
                "tag_name": "v1.2.3",
                "assets": [
                    {
                        "name": "ubuntu-x64.tar.gz",
                        "browser_download_url": "https://example.com/ubuntu-x64.tar.gz",
                    }
                ],
            }

            # Mock extract
            mock_extract.return_value = [str(tmp_path / "llama-cli")]

            # Mock get_llama_cpp_binary
            mock_get_binary.return_value = tmp_path / "llama-cli"

            # Mock subprocess.run with error
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stderr = "Error: something went wrong"
            mock_run.return_value = mock_result

            result = download_llama_cpp(bin_dir=tmp_path)

            assert result == tmp_path
