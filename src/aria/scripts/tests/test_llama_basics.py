"""Tests for basic utility functions in llama.py."""

import os
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from aria.scripts.llama import (
    _is_linux,
    _is_macos,
    _is_openblas_available,
    _is_ubuntu,
    _is_windows,
    _make_executable,
    _verify_binary,
)


class TestIsLinux:
    """Tests for _is_linux() function."""

    def test_returns_true_on_linux(self):
        """Test that _is_linux returns True on Linux."""
        with patch("platform.system", return_value="Linux"):
            assert _is_linux() is True

    def test_returns_false_on_windows(self):
        """Test that _is_linux returns False on Windows."""
        with patch("platform.system", return_value="Windows"):
            assert _is_linux() is False

    def test_returns_false_on_macos(self):
        """Test that _is_linux returns False on macOS."""
        with patch("platform.system", return_value="Darwin"):
            assert _is_linux() is False

    def test_returns_false_on_other_os(self):
        """Test that _is_linux returns False on other OS."""
        with patch("platform.system", return_value="FreeBSD"):
            assert _is_linux() is False


class TestIsUbuntu:
    """Tests for _is_ubuntu() function."""

    def test_returns_true_on_ubuntu(self, mock_platform_linux):
        """Test that _is_ubuntu returns True on Ubuntu."""
        with patch("builtins.open") as mock_open:
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
            assert _is_ubuntu() is True

    def test_returns_false_on_debian(self, mock_platform_linux):
        """Test that _is_ubuntu returns False on Debian."""
        with patch("builtins.open") as mock_open:
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = """
PRETTY_NAME="Debian GNU/Linux 12 (bookworm)"
NAME="Debian GNU/Linux"
VERSION_ID="12"
"""
            mock_open.return_value = mock_file
            assert _is_ubuntu() is False

    def test_returns_false_on_fedora(self, mock_platform_linux):
        """Test that _is_ubuntu returns False on Fedora."""
        with patch("builtins.open") as mock_open:
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = """
NAME="Fedora Linux"
VERSION="39 (Workstation Edition)"
ID=fedora
"""
            mock_open.return_value = mock_file
            assert _is_ubuntu() is False

    def test_returns_false_on_non_linux(self):
        """Test that _is_ubuntu returns False on non-Linux."""
        with patch("platform.system", return_value="Windows"):
            assert _is_ubuntu() is False

    def test_handles_missing_os_release(self, mock_platform_linux):
        """Test that _is_ubuntu handles missing /etc/os-release gracefully."""
        with patch("builtins.open") as mock_open:
            mock_open.side_effect = FileNotFoundError(
                "/etc/os-release not found"
            )
            assert _is_ubuntu() is False

    def test_handles_io_error(self, mock_platform_linux):
        """Test that _is_ubuntu handles IO errors gracefully."""
        with patch("builtins.open") as mock_open:
            mock_open.side_effect = IOError("Permission denied")
            assert _is_ubuntu() is False

    def test_case_insensitive_ubuntu_detection(self, mock_platform_linux):
        """Test that _is_ubuntu handles case variations in Ubuntu name."""
        with patch("builtins.open") as mock_open:
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = """
NAME="UBUNTU"
ID=UBUNTU
"""
            mock_open.return_value = mock_file
            assert _is_ubuntu() is True


class TestVerifyBinary:
    """Tests for _verify_binary() function."""

    def test_returns_true_for_existing_executable(self, tmp_path: Path):
        """Test that _verify_binary returns True for existing executable."""
        binary_path = tmp_path / "test_binary"
        binary_path.write_text("#!/bin/bash\necho test")
        binary_path.chmod(0o755)

        assert _verify_binary(binary_path) is True

    def test_returns_false_for_nonexistent_file(self, tmp_path: Path):
        """Test that _verify_binary returns False for non-existent file."""
        binary_path = tmp_path / "nonexistent_binary"
        assert _verify_binary(binary_path) is False

    def test_returns_false_for_non_executable(self, tmp_path: Path):
        """Test that _verify_binary returns False for non-executable file."""
        binary_path = tmp_path / "test_binary"
        binary_path.write_text("#!/bin/bash\necho test")
        binary_path.chmod(0o644)

        assert _verify_binary(binary_path) is False

    def test_returns_false_for_directory_without_execute_permission(
        self, tmp_path: Path
    ):
        """Returns False for a directory without execute permission."""
        dir_path = tmp_path / "test_dir"
        dir_path.mkdir()
        # Remove execute permission
        dir_path.chmod(0o644)

        assert _verify_binary(dir_path) is False

    def test_returns_true_for_directory_with_execute_permission(
        self, tmp_path: Path
    ):
        """Returns True for a directory with execute permission."""
        dir_path = tmp_path / "test_dir"
        dir_path.mkdir()
        # Add execute permission (directories need execute to be traversable)
        dir_path.chmod(0o755)

        # Directory exists and has execute permission
        assert _verify_binary(dir_path) is True


class TestMakeExecutable:
    """Tests for _make_executable() function."""

    def test_adds_execute_permission(self, tmp_path: Path):
        """Test that _make_executable adds execute permission."""
        file_path = tmp_path / "test_file"
        file_path.write_text("test content")
        # Start with no execute permission
        file_path.chmod(0o644)

        _make_executable(file_path)

        # Check that execute permission is set
        mode = os.stat(file_path).st_mode
        assert mode & 0o111 != 0

    def test_preserves_existing_permissions(self, tmp_path: Path):
        """Test that _make_executable preserves other permissions."""
        file_path = tmp_path / "test_file"
        file_path.write_text("test content")
        # Start with read/write for owner, read for group and others
        file_path.chmod(0o644)

        _make_executable(file_path)

        # Check that read/write permissions are preserved
        mode = os.stat(file_path).st_mode
        assert mode & 0o600 == 0o600  # Owner read/write
        assert mode & 0o40 == 0o40  # Group read
        assert mode & 0o4 == 0o4  # Others read

    def test_works_on_file_without_any_permissions(self, tmp_path: Path):
        """Test that _make_executable works on file with no permissions."""
        file_path = tmp_path / "test_file"
        file_path.write_text("test content")
        # Start with no permissions
        file_path.chmod(0o000)

        _make_executable(file_path)

        # Check that execute permission is set
        mode = os.stat(file_path).st_mode
        assert mode & 0o111 != 0


class TestIsOpenblasAvailable:
    """Tests for _is_openblas_available() function."""

    def test_returns_true_when_pkg_config_succeeds(self):
        """Returns True when pkg-config reports openblas is present."""
        mock_result = Mock()
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result):
            assert _is_openblas_available() is True

    def test_returns_true_when_linux_openblas_header_exists(self):
        """Returns True when /usr/include/openblas/cblas.h exists."""
        mock_pkg_fail = Mock()
        mock_pkg_fail.returncode = 1

        def fake_exists(self):
            return str(self) == "/usr/include/openblas/cblas.h"

        with (
            patch("subprocess.run", return_value=mock_pkg_fail),
            patch("pathlib.Path.exists", fake_exists),
        ):
            assert _is_openblas_available() is True

    def test_returns_true_when_linux_cblas_header_exists(self):
        """Returns True when /usr/include/cblas.h exists."""
        mock_pkg_fail = Mock()
        mock_pkg_fail.returncode = 1

        def fake_exists(self):
            return str(self) == "/usr/include/cblas.h"

        with (
            patch("subprocess.run", return_value=mock_pkg_fail),
            patch("pathlib.Path.exists", fake_exists),
        ):
            assert _is_openblas_available() is True

    def test_returns_true_when_macos_homebrew_arm_header_exists(self):
        """Returns True for macOS Apple Silicon Homebrew path."""
        mock_pkg_fail = Mock()
        mock_pkg_fail.returncode = 1

        def fake_exists(self):
            return str(self) == "/opt/homebrew/opt/openblas/include/cblas.h"

        with (
            patch("subprocess.run", return_value=mock_pkg_fail),
            patch("pathlib.Path.exists", fake_exists),
        ):
            assert _is_openblas_available() is True

    def test_returns_true_when_macos_homebrew_intel_header_exists(self):
        """Returns True for macOS Intel Homebrew path."""
        mock_pkg_fail = Mock()
        mock_pkg_fail.returncode = 1

        def fake_exists(self):
            return str(self) == "/usr/local/opt/openblas/include/cblas.h"

        with (
            patch("subprocess.run", return_value=mock_pkg_fail),
            patch("pathlib.Path.exists", fake_exists),
        ):
            assert _is_openblas_available() is True

    def test_returns_true_when_ldconfig_finds_libopenblas(self):
        """Returns True when ldconfig output contains libopenblas."""
        mock_pkg_fail = Mock()
        mock_pkg_fail.returncode = 1

        mock_ldconfig = Mock()
        mock_ldconfig.returncode = 0
        mock_ldconfig.stdout = (
            "\tlibopenblas.so.0 (libc6,x86-64)"
            " => /usr/lib/libopenblas.so.0\n"
        )

        def fake_exists(self):
            return False

        with (
            patch(
                "subprocess.run",
                side_effect=[mock_pkg_fail, mock_ldconfig],
            ),
            patch("pathlib.Path.exists", fake_exists),
        ):
            assert _is_openblas_available() is True

    def test_returns_false_when_all_checks_fail(self):
        """Returns False when pkg-config, headers, and ldconfig all fail."""
        mock_pkg_fail = Mock()
        mock_pkg_fail.returncode = 1

        mock_ldconfig_fail = Mock()
        mock_ldconfig_fail.returncode = 1
        mock_ldconfig_fail.stdout = ""

        def fake_exists(self):
            return False

        with (
            patch(
                "subprocess.run",
                side_effect=[mock_pkg_fail, mock_ldconfig_fail],
            ),
            patch("pathlib.Path.exists", fake_exists),
        ):
            assert _is_openblas_available() is False

    def test_returns_false_when_pkg_config_not_installed(self):
        """Returns False gracefully when pkg-config binary is not installed."""

        def fake_exists(self):
            return False

        with (
            patch(
                "subprocess.run",
                side_effect=FileNotFoundError("pkg-config not found"),
            ),
            patch("pathlib.Path.exists", fake_exists),
        ):
            assert _is_openblas_available() is False

    def test_returns_false_when_ldconfig_not_available(self):
        """Returns False gracefully when ldconfig is absent (e.g. macOS)."""
        mock_pkg_fail = Mock()
        mock_pkg_fail.returncode = 1

        def fake_exists(self):
            return False

        with (
            patch(
                "subprocess.run",
                side_effect=[
                    mock_pkg_fail,
                    FileNotFoundError("ldconfig not found"),
                ],
            ),
            patch("pathlib.Path.exists", fake_exists),
        ):
            assert _is_openblas_available() is False


class TestIsMacos:
    """Tests for _is_macos() function."""

    def test_returns_true_on_macos(self):
        """Test that _is_macos returns True on macOS (Darwin)."""
        with patch("platform.system", return_value="Darwin"):
            assert _is_macos() is True

    def test_returns_false_on_linux(self):
        """Test that _is_macos returns False on Linux."""
        with patch("platform.system", return_value="Linux"):
            assert _is_macos() is False

    def test_returns_false_on_windows(self):
        """Test that _is_macos returns False on Windows."""
        with patch("platform.system", return_value="Windows"):
            assert _is_macos() is False

    def test_returns_false_on_other_os(self):
        """Test that _is_macos returns False on other OS."""
        with patch("platform.system", return_value="FreeBSD"):
            assert _is_macos() is False


class TestIsWindows:
    """Tests for _is_windows() function."""

    def test_returns_true_on_windows(self):
        """Test that _is_windows returns True on Windows."""
        with patch("platform.system", return_value="Windows"):
            assert _is_windows() is True

    def test_returns_false_on_linux(self):
        """Test that _is_windows returns False on Linux."""
        with patch("platform.system", return_value="Linux"):
            assert _is_windows() is False

    def test_returns_false_on_macos(self):
        """Test that _is_windows returns False on macOS."""
        with patch("platform.system", return_value="Darwin"):
            assert _is_windows() is False

    def test_returns_false_on_other_os(self):
        """Test that _is_windows returns False on other OS."""
        with patch("platform.system", return_value="FreeBSD"):
            assert _is_windows() is False
