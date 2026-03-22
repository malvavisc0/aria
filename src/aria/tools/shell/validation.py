"""Command validation logic for shell execution tools.

This module provides security validation functions for shell commands,
including blocked command detection, shell operator detection, and
working directory validation.
"""

from pathlib import Path
from typing import Optional

from aria.tools.shell.constants import BASE_DIR, BLOCKED_COMMANDS
from aria.tools.shell.exceptions import (
    CommandBlockedError,
    WorkingDirectoryError,
)


def _extract_command_name(command: str) -> str:
    """Extract the base command name from a command string.

    Args:
        command: The full command string.

    Returns:
        The first word (command name), or empty string if blank.
    """
    stripped = command.strip()
    return stripped.split()[0] if stripped else ""


def _is_blocked_command(command: str) -> bool:
    """Check if a command name is in the blocked list.

    Args:
        command: The full command string.

    Returns:
        True if the base command name is blocked, False otherwise.
    """
    cmd_name = _extract_command_name(command)

    return cmd_name in BLOCKED_COMMANDS


def _validate_command(command: str) -> None:
    """Validate a command before execution.

    Args:
        command: The shell command to validate.

    Raises:
        CommandBlockedError: If the command is blocked or contains
            shell operators that could bypass the blocked list.
        ValueError: If the command is empty or too long.
    """
    if not command or not command.strip():
        raise ValueError("Command cannot be empty")

    if len(command) > 10000:
        raise ValueError("Command too long")

    if _is_blocked_command(command):
        raise CommandBlockedError(
            f"Command '{command}' is blocked for security reasons"
        )


def _validate_working_dir(working_dir: Optional[str]) -> Path:
    """Validate and resolve the working directory.

    Args:
        working_dir: The working directory path.

    Returns:
        Resolved Path object for the working directory.

    Raises:
        WorkingDirectoryError: If the working directory is invalid.
    """
    if working_dir is None:
        return BASE_DIR

    try:
        path = Path(working_dir).resolve()
    except (OSError, ValueError) as exc:
        raise WorkingDirectoryError(
            f"Invalid working directory path: {exc}"
        ) from exc

    if not path.exists():
        raise WorkingDirectoryError(
            f"Working directory does not exist: {working_dir}"
        )
    if not path.is_dir():
        raise WorkingDirectoryError(
            f"Working directory is not a directory: {working_dir}"
        )
    return path
