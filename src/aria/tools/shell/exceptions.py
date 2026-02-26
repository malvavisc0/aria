"""Shell execution exceptions.

This module provides custom exception classes for shell execution errors.
"""


class ShellExecutionError(Exception):
    """Base exception for shell execution errors."""

    pass


class CommandBlockedError(ShellExecutionError):
    """Raised when a command is blocked or not in the safe list."""

    pass


class WorkingDirectoryError(ShellExecutionError):
    """Raised when the working directory is invalid or not allowed."""

    pass
