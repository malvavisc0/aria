"""Command validation logic for shell execution tools.

This module provides security validation functions for shell commands,
including blocked command detection, shell operator detection, and
working directory validation.
"""

import re
from pathlib import Path
from typing import Optional

from aria.tools.shell.constants import (
    BASE_DIR,
    BLOCKED_COMMANDS,
    BLOCKED_UNIX,
    BLOCKED_WINDOWS,
    IS_LINUX,
    IS_MACOS,
    IS_WINDOWS,
)
from aria.tools.shell.exceptions import (
    CommandBlockedError,
    WorkingDirectoryError,
)

# Shell operators that could be used for injection.
_SHELL_OPERATORS_RE = re.compile(
    r"[;|&`]"  # semicolon, pipe, ampersand, backtick
    r"|\$\("  # $( subshell
    r"|\|\|"  # logical OR
    r"|&&"  # logical AND
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

    Blocked list only — no implicit whitelist. Injection/operators are
    handled separately by ``_has_shell_operators``.

    Args:
        command: The full command string.

    Returns:
        True if the base command name is blocked, False otherwise.
    """
    cmd_name = _extract_command_name(command)

    if cmd_name in BLOCKED_COMMANDS:
        return True

    if IS_WINDOWS and cmd_name in BLOCKED_WINDOWS:
        return True

    if (IS_LINUX or IS_MACOS) and cmd_name in BLOCKED_UNIX:
        return True

    return False


def _has_shell_operators(command: str) -> bool:
    """Check if a command contains shell operators that could bypass security.

    Detects pipes, semicolons, &&, ||, backticks, and $() subshells.

    Args:
        command: The full command string.

    Returns:
        True if shell operators are found.
    """
    return bool(_SHELL_OPERATORS_RE.search(command))


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

    if _has_shell_operators(command):
        raise CommandBlockedError(
            f"Command '{command}' contains shell operators "
            "(pipes, chains, or subshells are not allowed)"
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
