"""Tests for installation functions in llama.py."""

import subprocess
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from aria.scripts.llama import download_llama_cpp


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
        """Test that download_llama_cpp downloads pre-built binary on Ubuntu without nvcc."""
        with (
            patch("platform.system", return_value="Linux"),
            patch("builtins.open") as mock_open,
            patch("aria.scripts.llama._nvcc_available", return_value=False),
            patch(
                "aria.scripts.llama._get_latest_release_info"
            ) as mock_release,
            patch("aria.scripts.llama._download_and_extract") as mock_extract,
            patch(
                "aria.scripts.llama.get_llama_cpp_binary"
            ) as mock_get_binary,
            patch("aria.scripts.llama._make_executable"),
            patch("shutil.copy2"),
            patch("subprocess.run") as mock_run,
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
                "tag_name": "b5000",
                "assets": [
                    {
                        "name": "llama-b5000-bin-ubuntu-x64.tar.gz",
                        "browser_download_url": "https://example.com/ubuntu-x64.tar.gz",
                    }
                ],
            }

            # Mock extract
            mock_extract.return_value = [str(tmp_path / "llama-cli")]

            # Mock get_llama_cpp_binary
            mock_get_binary.return_value = tmp_path / "llama-server"

            # Mock subprocess.run for binary test
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "version b5000"
            mock_run.return_value = mock_result

            result = download_llama_cpp(bin_dir=tmp_path)

            assert result == tmp_path
            mock_extract.assert_called_once()

    def test_raises_error_when_no_linux_binary(self, tmp_path: Path):
        """Test that download_llama_cpp raises error when no Linux binary found."""
        with (
            patch("platform.system", return_value="Linux"),
            patch("builtins.open") as mock_open,
            patch("aria.scripts.llama._nvcc_available", return_value=False),
            patch(
                "aria.scripts.llama._get_latest_release_info"
            ) as mock_release,
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
                "tag_name": "b5000",
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
            patch(
                "aria.scripts.llama._get_latest_release_info"
            ) as mock_release,
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
                "tag_name": "b5000",
                "assets": [{"name": "ubuntu-x64.tar.gz"}],
            }

            with pytest.raises(RuntimeError) as exc_info:
                download_llama_cpp(bin_dir=tmp_path)

            assert "Could not find download URL" in str(exc_info.value)

    def test_raises_runtime_error_on_network_failure(self, tmp_path: Path):
        """Test that download_llama_cpp raises RuntimeError when GitHub API fails."""
        with (
            patch("platform.system", return_value="Linux"),
            patch("builtins.open") as mock_open,
            patch("aria.scripts.llama._nvcc_available", return_value=False),
            patch(
                "aria.scripts.llama._get_latest_release_info"
            ) as mock_release,
        ):
            # Mock Ubuntu OS release
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = """
NAME="Ubuntu"
VERSION="22.04.3 LTS (Jammy Jellyfish)"
ID=ubuntu
"""
            mock_open.return_value = mock_file

            # Mock network error on GitHub API
            mock_release.side_effect = urllib.error.URLError("Network error")

            with pytest.raises(RuntimeError) as exc_info:
                download_llama_cpp(bin_dir=tmp_path)

            assert "Failed to fetch release info" in str(exc_info.value)


class TestDownloadLatestLlamaCppUbuntuWithNvcc:
    """Tests for download_llama_cpp() on Ubuntu with nvcc (CUDA) — compiles from source."""

    def test_compiles_from_source_with_cuda_and_blas_when_openblas_available(
        self, tmp_path: Path
    ):
        """Test that BLAS is enabled when OpenBLAS is detected (Ubuntu + nvcc)."""
        with (
            patch("platform.system", return_value="Linux"),
            patch("builtins.open") as mock_open,
            patch("aria.scripts.llama._nvcc_available", return_value=True),
            patch(
                "aria.scripts.llama._is_openblas_available", return_value=True
            ),
            patch(
                "aria.scripts.llama._get_latest_release_info"
            ) as mock_release,
            patch(
                "aria.scripts.llama._download_and_extract_zip"
            ) as mock_extract_zip,
            patch(
                "aria.scripts.llama.install_llama_cpp_from_source"
            ) as mock_compile,
            patch("aria.scripts.llama._copy_binaries_and_libs"),
            patch("aria.scripts.llama._test_binary"),
            patch("shutil.rmtree"),
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
                "tag_name": "b5000",
                "assets": [
                    {
                        "name": "llama-b5000-bin-ubuntu-x64.tar.gz",
                        "browser_download_url": "https://example.com/ubuntu-x64.tar.gz",
                    }
                ],
            }

            # Mock extract_zip
            mock_extract_zip.return_value = (
                tmp_path / "source" / "llama.cpp-b5000"
            )

            # Mock compile
            mock_compile.return_value = tmp_path / "build"

            result = download_llama_cpp(bin_dir=tmp_path)

            assert result == tmp_path
            mock_compile.assert_called_once()
            call_kwargs = mock_compile.call_args.kwargs
            assert call_kwargs["use_cuda"] is True
            assert call_kwargs["use_blas"] is True

    def test_compiles_from_source_with_cuda_no_blas_when_openblas_missing(
        self, tmp_path: Path
    ):
        """Test that BLAS is disabled when OpenBLAS is not detected (Ubuntu + nvcc)."""
        with (
            patch("platform.system", return_value="Linux"),
            patch("builtins.open") as mock_open,
            patch("aria.scripts.llama._nvcc_available", return_value=True),
            patch(
                "aria.scripts.llama._is_openblas_available", return_value=False
            ),
            patch(
                "aria.scripts.llama._get_latest_release_info"
            ) as mock_release,
            patch(
                "aria.scripts.llama._download_and_extract_zip"
            ) as mock_extract_zip,
            patch(
                "aria.scripts.llama.install_llama_cpp_from_source"
            ) as mock_compile,
            patch("aria.scripts.llama._copy_binaries_and_libs"),
            patch("aria.scripts.llama._test_binary"),
            patch("shutil.rmtree"),
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
                "tag_name": "b5000",
                "assets": [
                    {
                        "name": "llama-b5000-bin-ubuntu-x64.tar.gz",
                        "browser_download_url": "https://example.com/ubuntu-x64.tar.gz",
                    }
                ],
            }

            # Mock extract_zip
            mock_extract_zip.return_value = (
                tmp_path / "source" / "llama.cpp-b5000"
            )

            # Mock compile
            mock_compile.return_value = tmp_path / "build"

            result = download_llama_cpp(bin_dir=tmp_path)

            assert result == tmp_path
            mock_compile.assert_called_once()
            call_kwargs = mock_compile.call_args.kwargs
            assert call_kwargs["use_cuda"] is True
            assert call_kwargs["use_blas"] is False


class TestDownloadLatestLlamaCppNonUbuntuLinux:
    """Tests for download_llama_cpp() on non-Ubuntu Linux."""

    def test_compiles_from_source_without_cuda(self, tmp_path: Path):
        """Test that download_llama_cpp compiles from source without CUDA on non-Ubuntu Linux."""
        with (
            patch("platform.system", return_value="Linux"),
            patch("builtins.open") as mock_open,
            patch("aria.scripts.llama._nvcc_available", return_value=False),
            patch("aria.scripts.llama._is_ubuntu", return_value=False),
            patch(
                "aria.scripts.llama._get_latest_release_info"
            ) as mock_release,
            patch(
                "aria.scripts.llama._download_and_extract_zip"
            ) as mock_extract_zip,
            patch(
                "aria.scripts.llama.install_llama_cpp_from_source"
            ) as mock_compile,
            patch("aria.scripts.llama._copy_binaries_and_libs"),
            patch("aria.scripts.llama._test_binary"),
            patch("shutil.rmtree"),
        ):
            # Mock Arch Linux OS release
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = """
NAME="Arch Linux"
PRETTY_NAME="Arch Linux"
ID=arch
"""
            mock_open.return_value = mock_file

            # Mock release info
            mock_release.return_value = {
                "tag_name": "b5000",
                "assets": [
                    {
                        "name": "llama-b5000-bin-ubuntu-x64.tar.gz",
                        "browser_download_url": "https://example.com/ubuntu-x64.tar.gz",
                    }
                ],
            }

            # Mock extract_zip
            mock_extract_zip.return_value = (
                tmp_path / "source" / "llama.cpp-b5000"
            )

            # Mock compile
            mock_compile.return_value = tmp_path / "build"

            result = download_llama_cpp(bin_dir=tmp_path)

            assert result == tmp_path
            mock_compile.assert_called_once()
            # Verify CUDA is disabled when nvcc not available
            call_kwargs = mock_compile.call_args.kwargs
            assert call_kwargs["use_cuda"] is False
            assert call_kwargs["use_blas"] is False

    def test_compiles_from_source_with_cuda_and_blas_when_nvcc_and_openblas_available(
        self, tmp_path: Path
    ):
        """Test CUDA+BLAS enabled when nvcc and OpenBLAS are both available."""
        with (
            patch("platform.system", return_value="Linux"),
            patch("builtins.open") as mock_open,
            patch("aria.scripts.llama._nvcc_available", return_value=True),
            patch(
                "aria.scripts.llama._is_openblas_available", return_value=True
            ),
            patch("aria.scripts.llama._is_ubuntu", return_value=False),
            patch(
                "aria.scripts.llama._get_latest_release_info"
            ) as mock_release,
            patch(
                "aria.scripts.llama._download_and_extract_zip"
            ) as mock_extract_zip,
            patch(
                "aria.scripts.llama.install_llama_cpp_from_source"
            ) as mock_compile,
            patch("aria.scripts.llama._copy_binaries_and_libs"),
            patch("aria.scripts.llama._test_binary"),
            patch("shutil.rmtree"),
        ):
            # Mock Arch Linux OS release
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = """
NAME="Arch Linux"
PRETTY_NAME="Arch Linux"
ID=arch
"""
            mock_open.return_value = mock_file

            # Mock release info
            mock_release.return_value = {
                "tag_name": "b5000",
                "assets": [
                    {
                        "name": "llama-b5000-bin-ubuntu-x64.tar.gz",
                        "browser_download_url": "https://example.com/ubuntu-x64.tar.gz",
                    }
                ],
            }

            # Mock extract_zip
            mock_extract_zip.return_value = (
                tmp_path / "source" / "llama.cpp-b5000"
            )

            # Mock compile
            mock_compile.return_value = tmp_path / "build"

            result = download_llama_cpp(bin_dir=tmp_path)

            assert result == tmp_path
            mock_compile.assert_called_once()
            call_kwargs = mock_compile.call_args.kwargs
            assert call_kwargs["use_cuda"] is True
            assert call_kwargs["use_blas"] is True

    def test_compiles_from_source_with_cuda_no_blas_when_nvcc_available_openblas_missing(
        self, tmp_path: Path
    ):
        """Test CUDA enabled but BLAS disabled when nvcc available but OpenBLAS missing."""
        with (
            patch("platform.system", return_value="Linux"),
            patch("builtins.open") as mock_open,
            patch("aria.scripts.llama._nvcc_available", return_value=True),
            patch(
                "aria.scripts.llama._is_openblas_available", return_value=False
            ),
            patch("aria.scripts.llama._is_ubuntu", return_value=False),
            patch(
                "aria.scripts.llama._get_latest_release_info"
            ) as mock_release,
            patch(
                "aria.scripts.llama._download_and_extract_zip"
            ) as mock_extract_zip,
            patch(
                "aria.scripts.llama.install_llama_cpp_from_source"
            ) as mock_compile,
            patch("aria.scripts.llama._copy_binaries_and_libs"),
            patch("aria.scripts.llama._test_binary"),
            patch("shutil.rmtree"),
        ):
            # Mock Arch Linux OS release
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = """
NAME="Arch Linux"
PRETTY_NAME="Arch Linux"
ID=arch
"""
            mock_open.return_value = mock_file

            # Mock release info
            mock_release.return_value = {
                "tag_name": "b5000",
                "assets": [
                    {
                        "name": "llama-b5000-bin-ubuntu-x64.tar.gz",
                        "browser_download_url": "https://example.com/ubuntu-x64.tar.gz",
                    }
                ],
            }

            # Mock extract_zip
            mock_extract_zip.return_value = (
                tmp_path / "source" / "llama.cpp-b5000"
            )

            # Mock compile
            mock_compile.return_value = tmp_path / "build"

            result = download_llama_cpp(bin_dir=tmp_path)

            assert result == tmp_path
            mock_compile.assert_called_once()
            call_kwargs = mock_compile.call_args.kwargs
            assert call_kwargs["use_cuda"] is True
            assert call_kwargs["use_blas"] is False


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
            patch(
                "aria.scripts.llama.get_llama_cpp_binary"
            ) as mock_get_binary,
            patch("aria.scripts.llama._make_executable"),
            patch("shutil.copy2"),
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
                "tag_name": "b4500",
                "assets": [
                    {
                        "name": "llama-b4500-bin-ubuntu-x64.tar.gz",
                        "browser_download_url": "https://example.com/ubuntu-x64.tar.gz",
                    }
                ],
            }

            # Mock extract
            mock_extract.return_value = [str(tmp_path / "llama-cli")]

            # Mock get_llama_cpp_binary
            mock_get_binary.return_value = tmp_path / "llama-server"

            # Mock subprocess.run for binary test
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "version b4500"
            mock_run.return_value = mock_result

            result = download_llama_cpp(bin_dir=tmp_path, version="b4500")

            assert result == tmp_path
            mock_release.assert_called_once_with("b4500")

    def test_downloads_latest_when_version_is_latest(self, tmp_path: Path):
        """Test that download_llama_cpp downloads latest when version is 'latest'."""
        with (
            patch("platform.system", return_value="Linux"),
            patch("builtins.open") as mock_open,
            patch("aria.scripts.llama._nvcc_available", return_value=False),
            patch(
                "aria.scripts.llama._get_latest_release_info"
            ) as mock_release,
            patch("aria.scripts.llama._download_and_extract") as mock_extract,
            patch(
                "aria.scripts.llama.get_llama_cpp_binary"
            ) as mock_get_binary,
            patch("aria.scripts.llama._make_executable"),
            patch("shutil.copy2"),
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
                "tag_name": "b5000",
                "assets": [
                    {
                        "name": "llama-b5000-bin-ubuntu-x64.tar.gz",
                        "browser_download_url": "https://example.com/ubuntu-x64.tar.gz",
                    }
                ],
            }

            # Mock extract
            mock_extract.return_value = [str(tmp_path / "llama-cli")]

            # Mock get_llama_cpp_binary
            mock_get_binary.return_value = tmp_path / "llama-server"

            # Mock subprocess.run for binary test
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "version b5000"
            mock_run.return_value = mock_result

            result = download_llama_cpp(bin_dir=tmp_path, version="latest")

            assert result == tmp_path
            mock_release.assert_called_once()


class TestDownloadLatestLlamaCppBinaryTesting:
    """Tests for binary testing in download_llama_cpp()."""

    def test_tests_binary_after_prebuilt_installation(self, tmp_path: Path):
        """Test that download_llama_cpp tests binary after pre-built installation."""
        with (
            patch("platform.system", return_value="Linux"),
            patch("builtins.open") as mock_open,
            patch("aria.scripts.llama._nvcc_available", return_value=False),
            patch("aria.scripts.llama._is_cuda_available", return_value=False),
            patch(
                "aria.scripts.llama._get_latest_release_info"
            ) as mock_release,
            patch("aria.scripts.llama._download_and_extract") as mock_extract,
            patch(
                "aria.scripts.llama.get_llama_cpp_binary"
            ) as mock_get_binary,
            patch("aria.scripts.llama._make_executable"),
            patch("shutil.copy2"),
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
                "tag_name": "b5000",
                "assets": [
                    {
                        "name": "llama-b5000-bin-ubuntu-x64.tar.gz",
                        "browser_download_url": "https://example.com/ubuntu-x64.tar.gz",
                    }
                ],
            }

            # Mock extract
            mock_extract.return_value = [str(tmp_path / "llama-cli")]

            # Mock get_llama_cpp_binary
            mock_get_binary.return_value = tmp_path / "llama-server"

            # Mock subprocess.run for binary test
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "version b5000"
            mock_run.return_value = mock_result

            result = download_llama_cpp(bin_dir=tmp_path)

            assert result == tmp_path
            # Binary testing IS performed for pre-built binaries
            mock_run.assert_called_once()

    def test_handles_binary_test_timeout(self, tmp_path: Path):
        """Test that download_llama_cpp handles binary test timeout gracefully."""
        with (
            patch("platform.system", return_value="Linux"),
            patch("builtins.open") as mock_open,
            patch("aria.scripts.llama._nvcc_available", return_value=False),
            patch("aria.scripts.llama._is_cuda_available", return_value=False),
            patch(
                "aria.scripts.llama._get_latest_release_info"
            ) as mock_release,
            patch("aria.scripts.llama._download_and_extract") as mock_extract,
            patch(
                "aria.scripts.llama.get_llama_cpp_binary"
            ) as mock_get_binary,
            patch("aria.scripts.llama._make_executable"),
            patch("shutil.copy2"),
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
                "tag_name": "b5000",
                "assets": [
                    {
                        "name": "llama-b5000-bin-ubuntu-x64.tar.gz",
                        "browser_download_url": "https://example.com/ubuntu-x64.tar.gz",
                    }
                ],
            }

            # Mock extract
            mock_extract.return_value = [str(tmp_path / "llama-cli")]

            # Mock get_llama_cpp_binary
            mock_get_binary.return_value = tmp_path / "llama-server"

            # Mock subprocess.run to raise TimeoutExpired
            mock_run.side_effect = subprocess.TimeoutExpired(
                "llama-server", 10
            )

            # Should not raise — timeout is handled gracefully
            result = download_llama_cpp(bin_dir=tmp_path)

            assert result == tmp_path

    def test_handles_binary_test_failure(self, tmp_path: Path):
        """Test that download_llama_cpp handles binary test failure gracefully."""
        with (
            patch("platform.system", return_value="Linux"),
            patch("builtins.open") as mock_open,
            patch("aria.scripts.llama._nvcc_available", return_value=False),
            patch(
                "aria.scripts.llama._get_latest_release_info"
            ) as mock_release,
            patch("aria.scripts.llama._download_and_extract") as mock_extract,
            patch(
                "aria.scripts.llama.get_llama_cpp_binary"
            ) as mock_get_binary,
            patch("aria.scripts.llama._make_executable"),
            patch("shutil.copy2"),
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
                "tag_name": "b5000",
                "assets": [
                    {
                        "name": "llama-b5000-bin-ubuntu-x64.tar.gz",
                        "browser_download_url": "https://example.com/ubuntu-x64.tar.gz",
                    }
                ],
            }

            # Mock extract
            mock_extract.return_value = [str(tmp_path / "llama-cli")]

            # Mock get_llama_cpp_binary
            mock_get_binary.return_value = tmp_path / "llama-server"

            # Mock subprocess.run with error
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stderr = "Error: something went wrong"
            mock_run.return_value = mock_result

            # Should not raise — test failure is handled gracefully
            result = download_llama_cpp(bin_dir=tmp_path)

            assert result == tmp_path
