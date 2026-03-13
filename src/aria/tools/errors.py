"""Shared error handling infrastructure for all tool modules."""


class ToolError(Exception):
    """Base exception for all tool operations.

    Subclasses should define class-level attributes:
        code: Machine-readable error code
        recoverable: Whether the agent can retry
        how_to_fix: Recovery guidance for the agent
    """

    code: str = "INTERNAL_ERROR"
    recoverable: bool = False
    how_to_fix: str = "An unexpected error occurred."
