"""Command validation logic for shell execution tools.

This module provides security validation functions for shell commands,
including blocked command detection and working directory validation.
"""

import re
from pathlib import Path

from aria.tools.shell.constants import BASE_DIR, BLOCKED_COMMANDS
from aria.tools.shell.exceptions import (
    CommandBlockedError,
    WorkingDirectoryError,
)

# Shell operators that separate pipeline/command segments
_SHELL_OPERATORS = re.compile(r"\s*(?:\|{1,2}|&&|;)\s*")


def _extract_command_name(command: str) -> str:
    """Extract the base command name from a command string.

    Args:
        command: The full command string.

    Returns:
        The first word (command name), or empty string if blank.
    """
    stripped = command.strip()
    # Strip leading env assignments like VAR=val cmd ...
    parts = stripped.split()
    for i, part in enumerate(parts):
        if "=" not in part:
            return part
    return ""


def _extract_all_command_names(command: str) -> list[str]:
    """Extract command names from all segments of a shell pipeline.

    Splits on shell operators (|, ||, &&, ;) and extracts the first
    token of each segment, skipping env var assignments.

    Args:
        command: The full command string (may contain pipes/chains).

    Returns:
        List of command names found in each segment.
    """
    segments = _SHELL_OPERATORS.split(command)
    names = []
    for segment in segments:
        parts = segment.strip().split()
        for part in parts:
            if "=" not in part:
                names.append(part)
                break
    return names


def _is_blocked_command(command: str) -> bool:
    """Check if any command in a pipeline is in the blocked list.

    Args:
        command: The full command string (may contain pipes/chains).

    Returns:
        True if any command name is blocked, False otherwise.
    """
    cmd_names = _extract_all_command_names(command)
    return any(name in BLOCKED_COMMANDS for name in cmd_names)


def _validate_command(command: str) -> None:
    """Validate a command before execution.

    Args:
        command: The shell command to validate.

    Raises:
        CommandBlockedError: If the command contains a blocked command.
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


def _validate_working_dir(working_dir: str | None) -> Path:
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
        raise WorkingDirectoryError(f"Invalid working directory path: {exc}") from exc

    if not path.exists():
        raise WorkingDirectoryError(f"Working directory does not exist: {working_dir}")
    if not path.is_dir():
        raise WorkingDirectoryError(
            f"Working directory is not a directory: {working_dir}"
        )
    return path
