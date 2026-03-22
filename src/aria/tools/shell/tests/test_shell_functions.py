"""Tests for shell execution functions."""

import json
import tempfile
from pathlib import Path

import pytest

from aria.tools.shell import (
    execute_command,
    execute_command_batch,
    get_platform_info,
)
from aria.tools.shell.constants import IS_WINDOWS
from aria.tools.shell.exceptions import CommandBlockedError
from aria.tools.shell.validation import _is_blocked_command, _validate_command


class TestValidateCommand:
    """Tests for _validate_command and related helpers."""

    def test_empty_command_raises_value_error(self):
        """Test that an empty command raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            _validate_command("")

    def test_whitespace_only_raises_value_error(self):
        """Test that whitespace-only command raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            _validate_command("   ")

    def test_too_long_command_raises_value_error(self):
        """Test that an excessively long command raises ValueError."""
        with pytest.raises(ValueError, match="too long"):
            _validate_command("a" * 10001)

    def test_blocked_command_raises_error(self):
        """Test that a blocked command raises CommandBlockedError."""
        with pytest.raises(CommandBlockedError, match="blocked"):
            _validate_command("sudo rm -rf /")

    def test_blocked_command_shutdown(self):
        """Test that shutdown is blocked."""
        with pytest.raises(CommandBlockedError):
            _validate_command("shutdown -h now")

    def test_valid_command_passes(self):
        """Test that a valid command passes validation."""
        _validate_command("echo hello")  # Should not raise

    def test_is_blocked_command_detects_sudo(self):
        """Test _is_blocked_command detects sudo."""
        assert _is_blocked_command("sudo apt install foo") is True

    def test_is_blocked_command_allows_echo(self):
        """Test _is_blocked_command allows echo."""
        assert _is_blocked_command("echo hello") is False


class TestExecuteCommand:
    """Tests for execute_command function."""

    def test_execute_simple_command(self):
        """Test executing a simple echo command."""
        result = execute_command(
            intent="Test echo command",
            command_name="echo",
            args=["hello"],
            timeout=5,
        )
        data = json.loads(result)

        assert data["operation"] == "execute_command"
        assert data["result"]["return_code"] == 0
        assert "hello" in data["result"]["stdout"]
        assert data["result"]["timed_out"] is False

    def test_execute_command_with_timeout(self):
        """Test command execution with custom timeout."""
        result = execute_command(
            intent="Test sleep command",
            command_name="python",
            args=["-c", "import time; time.sleep(0.1)"],
            timeout=5,
        )
        data = json.loads(result)

        assert data["result"]["return_code"] == 0

    def test_execute_command_with_working_dir(self):
        """Test command execution with custom working directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = execute_command(
                intent="Test ls in temp dir",
                command_name="ls" if not IS_WINDOWS else "dir",
                args=[],
                timeout=5,
                working_dir=tmpdir,
            )
            data = json.loads(result)

            assert data["result"]["return_code"] == 0
            assert tmpdir in data["result"]["working_dir"]

    def test_execute_command_treats_shell_operators_as_literal_args(self):
        """Test that shell operators in args are treated as literal text."""
        result = execute_command(
            intent="Test literal args",
            command_name="echo",
            args=["hello | world"],
            timeout=5,
        )
        data = json.loads(result)

        assert data["result"]["return_code"] == 0
        assert "hello | world" in data["result"]["stdout"]

    def test_execute_command_timeout(self):
        """Test command execution timeout."""
        result = execute_command(
            intent="Test timeout",
            command_name="python",
            args=["-c", "import time; time.sleep(10)"],
            timeout=1,
        )
        data = json.loads(result)

        assert data["result"]["timed_out"] is True

    def test_execute_command_error_handling(self):
        """Test command execution with non-zero exit code."""
        result = execute_command(
            intent="Test error handling",
            command_name="python",
            args=["-c", "import sys; sys.exit(1)"],
            timeout=5,
        )
        data = json.loads(result)

        assert data["result"]["return_code"] == 1

    def test_execute_blocked_command_raises_error(self):
        """Test that executing a blocked command raises CommandBlockedError."""
        with pytest.raises(CommandBlockedError):
            execute_command(
                intent="Test blocked command",
                command_name="shutdown",
                args=[],
                timeout=5,
            )

    def test_response_has_metadata(self):
        """Test that response includes metadata with timestamp."""
        result = execute_command(
            intent="Test metadata",
            command_name="echo",
            args=["test"],
            timeout=5,
        )
        data = json.loads(result)

        assert "metadata" in data
        assert "timestamp" in data["metadata"]

    def test_response_has_platform(self):
        """Test that response includes platform info."""
        result = execute_command(
            intent="Test platform in response",
            command_name="echo",
            args=["test"],
            timeout=5,
        )
        data = json.loads(result)

        assert "platform" in data["result"]
        assert data["result"]["platform"] in ["windows", "linux", "darwin"]

    def test_execute_command_with_args(self):
        """Test executing command with arguments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("test content")

            result = execute_command(
                intent="Test cat command",
                command_name="cat" if not IS_WINDOWS else "type",
                args=[str(test_file)],
                timeout=5,
            )
            data = json.loads(result)

            assert data["result"]["return_code"] == 0
            assert "test content" in data["result"]["stdout"]

    def test_execute_command_not_found_returns_127(self):
        """Test that a whitelisted but missing command returns 127."""
        # vm_stat is in the safe list but only exists on macOS
        if not IS_WINDOWS:
            result = execute_command(
                intent="Test command not found",
                command_name="vm_stat",
                args=[],
                timeout=5,
            )
            data = json.loads(result)
            # On Linux, vm_stat won't be found
            # On macOS, it will succeed — both are valid outcomes
            assert data["result"]["return_code"] in [0, 127]


class TestExecuteCommandBatch:
    """Tests for execute_command_batch function."""

    def test_execute_batch_success(self):
        """Test executing a batch of successful commands."""
        commands = [
            {"command": "echo hello"},
            {"command": "echo world"},
        ]
        result = execute_command_batch(
            intent="Test batch execution",
            commands=commands,
            stop_on_error=True,
        )
        data = json.loads(result)

        assert data["operation"] == "execute_command_batch"
        assert data["result"]["success_count"] == 2
        assert data["result"]["failure_count"] == 0
        assert data["result"]["stopped_early"] is False

    def test_execute_batch_with_error(self):
        """Test executing a batch with one failing command."""
        commands = [
            {"command": "echo hello"},
            {"command": "exit 1"},
            {"command": "echo world"},
        ]
        result = execute_command_batch(
            intent="Test batch with error",
            commands=commands,
            stop_on_error=True,
        )
        data = json.loads(result)

        assert data["result"]["success_count"] == 1
        assert data["result"]["failure_count"] >= 1
        assert data["result"]["stopped_early"] is True

    def test_execute_batch_continue_on_error(self):
        """Test executing a batch with continue_on_error flag."""
        commands = [
            {"command": "echo hello"},
            {"command": "exit 1", "continue_on_error": True},
            {"command": "echo world"},
        ]
        result = execute_command_batch(
            intent="Test batch continue on error",
            commands=commands,
            stop_on_error=True,
        )
        data = json.loads(result)

        assert data["result"]["success_count"] == 2
        assert data["result"]["stopped_early"] is False

    def test_execute_batch_metadata(self):
        """Test that batch response includes metadata."""
        commands = [{"command": "echo test"}]
        result = execute_command_batch(
            intent="Test batch metadata",
            commands=commands,
        )
        data = json.loads(result)

        assert "metadata" in data
        assert data["metadata"]["total_commands"] == 1


class TestGetPlatformInfo:
    """Tests for get_platform_info function."""

    def test_get_platform_info(self):
        """Test getting platform information."""
        result = get_platform_info(intent="Test platform info")
        data = json.loads(result)

        assert data["operation"] == "get_platform_info"
        assert "os" in data["result"]
        assert "shell" in data["result"]
        assert "home" in data["result"]
        assert "path_separator" in data["result"]
        assert "temp_dir" in data["result"]

    def test_platform_info_contains_valid_os(self):
        """Test that platform info contains a valid OS value."""
        result = get_platform_info(intent="Test platform info fields")
        data = json.loads(result)

        # CURRENT_OS returns "darwin" for macOS, not "macos"
        assert data["result"]["os"] in ["windows", "linux", "darwin"]

    def test_platform_info_path_separator(self):
        """Test that path separator matches the OS."""
        result = get_platform_info(intent="Test path separator")
        data = json.loads(result)

        if data["result"]["os"] == "windows":
            assert data["result"]["path_separator"] == "\\"
        else:
            assert data["result"]["path_separator"] == "/"
