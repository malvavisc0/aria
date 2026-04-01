"""Tests for shell execution functions."""

import json
import tempfile
from pathlib import Path

import pytest

from aria.tools.shell import shell
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


class TestShellSingleCommand:
    """Tests for shell function with a single command (batch format)."""

    def _get_result_data(self, result: str) -> dict:
        """Parse result and return the first command's data dict."""
        data = json.loads(result)
        # shell() always returns batch format: data["results"][0]["data"]
        return data["data"]["results"][0]["data"]

    def _get_result_envelope(self, result: str) -> dict:
        """Parse result and return the top-level envelope."""
        return json.loads(result)

    def test_execute_simple_command(self):
        """Test executing a simple echo command."""
        result = shell(
            reason="Test echo command",
            commands={"command_name": "echo", "args": ["hello"]},
            timeout=5,
        )
        envelope = self._get_result_envelope(result)
        cmd_data = self._get_result_data(result)

        assert envelope["tool"] == "shell"
        assert cmd_data["return_code"] == 0
        assert "hello" in cmd_data["stdout"]
        assert cmd_data["timed_out"] is False

    def test_execute_command_with_timeout(self):
        """Test command execution with custom timeout."""
        result = shell(
            reason="Test sleep command",
            commands={
                "command_name": "python",
                "args": ["-c", "import time; time.sleep(0.1)"],
            },
            timeout=5,
        )
        cmd_data = self._get_result_data(result)

        assert cmd_data["return_code"] == 0

    def test_execute_command_with_working_dir(self):
        """Test command execution with custom working directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = shell(
                reason="Test ls in temp dir",
                commands={
                    "command_name": "ls" if not IS_WINDOWS else "dir",
                    "args": [],
                },
                timeout=5,
                working_dir=tmpdir,
            )
            cmd_data = self._get_result_data(result)

            assert cmd_data["return_code"] == 0
            assert tmpdir in cmd_data["working_dir"]

    def test_execute_command_treats_shell_operators_as_literal_args(self):
        """Test that shell operators in args are treated as literal text."""
        result = shell(
            reason="Test literal args",
            commands={
                "command_name": "echo",
                "args": ["hello | world"],
            },
            timeout=5,
        )
        cmd_data = self._get_result_data(result)

        assert cmd_data["return_code"] == 0
        assert "hello | world" in cmd_data["stdout"]

    def test_execute_command_timeout(self):
        """Test command execution timeout."""
        result = shell(
            reason="Test timeout",
            commands={
                "command_name": "python",
                "args": ["-c", "import time; time.sleep(10)"],
            },
            timeout=1,
        )
        cmd_data = self._get_result_data(result)

        assert cmd_data["timed_out"] is True

    def test_execute_command_error_handling(self):
        """Test command execution with non-zero exit code."""
        result = shell(
            reason="Test error handling",
            commands={
                "command_name": "python",
                "args": ["-c", "import sys; sys.exit(1)"],
            },
            timeout=5,
        )
        cmd_data = self._get_result_data(result)

        assert cmd_data["return_code"] == 1

    def test_execute_blocked_command_returns_error(self):
        """Test that executing a blocked command returns an error result."""
        result = shell(
            reason="Test blocked command",
            commands={"command_name": "shutdown", "args": []},
            timeout=5,
        )
        data = json.loads(result)

        assert data["data"]["failure_count"] == 1
        assert data["data"]["success_count"] == 0
        assert "blocked" in data["data"]["results"][0]["error"].lower()

    def test_response_has_timestamp(self):
        """Test that response includes timestamp at top level."""
        result = shell(
            reason="Test metadata",
            commands={"command_name": "echo", "args": ["test"]},
            timeout=5,
        )
        envelope = self._get_result_envelope(result)

        assert "timestamp" in envelope

    def test_response_has_platform(self):
        """Test that response includes platform info."""
        result = shell(
            reason="Test platform in response",
            commands={"command_name": "echo", "args": ["test"]},
            timeout=5,
        )
        cmd_data = self._get_result_data(result)

        assert "platform" in cmd_data
        assert cmd_data["platform"] in ["windows", "linux", "darwin"]

    def test_execute_command_with_args(self):
        """Test executing command with arguments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("test content")

            result = shell(
                reason="Test cat command",
                commands={
                    "command_name": "cat" if not IS_WINDOWS else "type",
                    "args": [str(test_file)],
                },
                timeout=5,
            )
            cmd_data = self._get_result_data(result)

            assert cmd_data["return_code"] == 0
            assert "test content" in cmd_data["stdout"]

    def test_execute_command_not_found_returns_127(self):
        """Test that a whitelisted but missing command returns 127."""
        # vm_stat is in the safe list but only exists on macOS
        if not IS_WINDOWS:
            result = shell(
                reason="Test command not found",
                commands={"command_name": "vm_stat", "args": []},
                timeout=5,
            )
            cmd_data = self._get_result_data(result)
            # On Linux, vm_stat won't be found
            # On macOS, it will succeed — both are valid outcomes
            assert cmd_data["return_code"] in [0, 127]

    def test_legacy_command_string_format(self):
        """Test legacy command string format (shlex split)."""
        result = shell(
            reason="Test legacy format",
            commands={"command": "echo hello world"},
            timeout=5,
        )
        cmd_data = self._get_result_data(result)

        assert cmd_data["return_code"] == 0
        assert "hello world" in cmd_data["stdout"]

    def test_single_command_has_batch_metadata(self):
        """Test that single dict input returns batch metadata."""
        result = shell(
            reason="Test batch metadata for single",
            commands={"command_name": "echo", "args": ["test"]},
            timeout=5,
        )
        data = json.loads(result)

        assert data["data"]["success_count"] == 1
        assert data["data"]["failure_count"] == 0
        assert data["data"]["stopped_early"] is False
        assert len(data["data"]["results"]) == 1


class TestShellBatch:
    """Tests for shell function with multiple commands."""

    def test_execute_batch_success(self):
        """Test executing a batch of successful commands."""
        commands = [
            {"command": "echo hello"},
            {"command": "echo world"},
        ]
        result = shell(
            reason="Test batch execution",
            commands=commands,
            stop_on_error=True,
        )
        data = json.loads(result)

        assert data["tool"] == "shell"
        assert data["data"]["success_count"] == 2
        assert data["data"]["failure_count"] == 0
        assert data["data"]["stopped_early"] is False

    def test_execute_batch_with_error(self):
        """Test executing a batch with one failing command."""
        commands = [
            {"command": "echo hello"},
            {"command": "exit 1"},
            {"command": "echo world"},
        ]
        result = shell(
            reason="Test batch with error",
            commands=commands,
            stop_on_error=True,
        )
        data = json.loads(result)

        assert data["data"]["success_count"] == 1
        assert data["data"]["failure_count"] >= 1
        assert data["data"]["stopped_early"] is True

    def test_execute_batch_continue_on_error(self):
        """Test executing a batch with continue_on_error flag."""
        commands = [
            {"command": "echo hello"},
            {"command": "exit 1", "continue_on_error": True},
            {"command": "echo world"},
        ]
        result = shell(
            reason="Test batch continue on error",
            commands=commands,
            stop_on_error=True,
        )
        data = json.loads(result)

        assert data["data"]["success_count"] == 2
        assert data["data"]["stopped_early"] is False

    def test_execute_batch_has_timestamp(self):
        """Test that batch response includes timestamp."""
        commands = [{"command": "echo test"}]
        result = shell(
            reason="Test batch metadata",
            commands=commands,
        )
        data = json.loads(result)

        assert "timestamp" in data
        assert data["data"]["success_count"] == 1

    def test_execute_empty_commands(self):
        """Test that empty commands list returns valid response."""
        result = shell(
            reason="Test empty commands",
            commands=[],
        )
        data = json.loads(result)

        assert data["data"]["success_count"] == 0
        assert data["data"]["failure_count"] == 0
