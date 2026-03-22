"""Unit tests for validation helpers in shell module.

These tests directly test the validation functions in validation.py,
providing comprehensive coverage of the security validation logic.
"""

import tempfile
from pathlib import Path

import pytest

from aria.tools.shell.exceptions import (
    CommandBlockedError,
    WorkingDirectoryError,
)
from aria.tools.shell.validation import (
    _extract_command_name,
    _is_blocked_command,
    _validate_command,
    _validate_working_dir,
)


class TestExtractCommandName:
    """Tests for _extract_command_name function."""

    def test_simple_command(self):
        """Test extracting command name from simple command."""
        assert _extract_command_name("ls -la") == "ls"

    def test_command_with_path(self):
        """Test extracting command name with path."""
        assert _extract_command_name("/usr/bin/ls") == "/usr/bin/ls"

    def test_empty_string(self):
        """Test empty string returns empty."""
        assert _extract_command_name("") == ""

    def test_whitespace_only(self):
        """Test whitespace only returns empty."""
        assert _extract_command_name("   ") == ""

    def test_command_with_args(self):
        """Test extracting command with multiple arguments."""
        assert _extract_command_name("git commit -m 'message'") == "git"


class TestIsBlockedCommand:
    """Tests for _is_blocked_command function."""

    def test_sudo_blocked(self):
        """Test that sudo is blocked."""
        assert _is_blocked_command("sudo rm -rf /") is True

    def test_shutdown_blocked(self):
        """Test that shutdown is blocked."""
        assert _is_blocked_command("shutdown -h now") is True

    def test_chmod_blocked(self):
        """Test that chmod is blocked."""
        assert _is_blocked_command("chmod 777 /") is True

    def test_safe_command_not_blocked(self):
        """Test that safe commands are not blocked."""
        assert _is_blocked_command("ls -la") is False
        assert _is_blocked_command("git status") is False
        assert _is_blocked_command("cat file.txt") is False


class TestValidateCommand:
    """Tests for _validate_command function."""

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
        """Test that valid commands pass validation."""
        # Should not raise any exception
        _validate_command("ls -la")
        _validate_command("git status")
        _validate_command("cat file.txt")


class TestValidateWorkingDir:
    """Tests for _validate_working_dir function."""

    def test_none_returns_base_dir(self):
        """Test that None returns BASE_DIR."""
        from aria.tools.shell.constants import BASE_DIR

        result = _validate_working_dir(None)
        assert result == BASE_DIR

    def test_valid_directory_returns_path(self):
        """Test that valid directory returns resolved Path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = _validate_working_dir(tmpdir)
            assert isinstance(result, Path)
            assert result.exists()
            assert result.is_dir()

    def test_nonexistent_directory_raises_error(self):
        """Test that nonexistent directory raises WorkingDirectoryError."""
        with pytest.raises(WorkingDirectoryError, match="does not exist"):
            _validate_working_dir("/nonexistent/path/12345")

    def test_file_not_directory_raises_error(self):
        """Test that a file path raises WorkingDirectoryError."""
        with tempfile.NamedTemporaryFile() as tmpfile:
            with pytest.raises(WorkingDirectoryError, match="not a directory"):
                _validate_working_dir(tmpfile.name)

    def test_invalid_path_raises_error(self):
        """Test that invalid path raises WorkingDirectoryError."""
        with pytest.raises(WorkingDirectoryError):
            # This should fail on most systems
            _validate_working_dir("\x00\x00\x00")
