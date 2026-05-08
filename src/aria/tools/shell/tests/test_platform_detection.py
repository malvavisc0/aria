"""Tests for shell platform detection."""

import platform
from unittest.mock import patch

import pytest

from aria.tools.shell.constants import (
    CURRENT_OS,
    IS_LINUX,
    IS_MACOS,
    IS_WINDOWS,
    detect_shell,
)


def test_current_os_detection():
    """Test that CURRENT_OS is correctly detected."""
    system = platform.system().lower()
    assert CURRENT_OS == system


def test_platform_constants():
    """Test that exactly one platform constant is True."""
    platform_count = sum([IS_WINDOWS, IS_MACOS, IS_LINUX])
    assert platform_count == 1


@pytest.mark.skipif(not IS_WINDOWS, reason="Windows-only test")
def test_detect_shell_windows():
    """Test shell detection on Windows."""
    shell = detect_shell()
    assert shell in ["powershell", "cmd"]


@pytest.mark.skipif(not IS_WINDOWS, reason="Windows-only test")
def test_detect_shell_windows_powershell():
    """Test that PowerShell is detected when PSMODULEPATH is set."""
    with patch.dict("os.environ", {"PSMODULEPATH": "C:\\something"}):
        shell = detect_shell()
        assert shell == "powershell"


@pytest.mark.skipif(not IS_WINDOWS, reason="Windows-only test")
def test_detect_shell_windows_cmd():
    """Test that CMD is detected when PSMODULEPATH is absent."""
    with patch.dict("os.environ", {}, clear=False):
        import os

        env = dict(os.environ)
        env.pop("PSMODULEPATH", None)
        with patch.dict("os.environ", env, clear=True):
            shell = detect_shell()
            assert shell == "cmd"


@pytest.mark.skipif(not (IS_LINUX or IS_MACOS), reason="Unix-only test")
def test_detect_shell_unix():
    """Test shell detection on Unix-like systems."""
    shell = detect_shell()
    # Shell could be a full path or just a name
    assert any(s in shell for s in ["bash", "zsh", "sh", "fish"]), (
        f"Unexpected shell: {shell}"
    )


@pytest.mark.skipif(not (IS_LINUX or IS_MACOS), reason="Unix-only test")
def test_detect_shell_unix_respects_env():
    """Test that Unix shell detection reads $SHELL."""
    with patch.dict("os.environ", {"SHELL": "/bin/zsh"}):
        shell = detect_shell()
        assert shell == "/bin/zsh"
