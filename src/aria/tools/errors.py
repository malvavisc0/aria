"""Shared error handling infrastructure for all tool modules."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


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


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def tool_error_response(
    tool: str,
    intent: str,
    exc: Exception,
    **context: Any,
) -> str:
    """Generate a standardized JSON error response from an exception.

    Args:
        tool: Name of the tool that generated the error.
        intent: The agent's stated intent for calling this tool.
        exc: The exception that occurred.
        **context: Additional tool-specific context fields.

    Returns:
        JSON string with standardized error format.
    """
    # Handle missing/empty intent with fallback
    if not intent or not intent.strip():
        intent = f"unspecified_{tool}_operation"
        logger.warning(
            f"Missing intent for tool '{tool}', using fallback: {intent}"
        )

    error_code = getattr(exc, "code", type(exc).__name__.upper())
    recoverable = getattr(exc, "recoverable", False)
    how_to_fix = getattr(exc, "how_to_fix", None)

    error_block: Dict[str, Any] = {
        "code": error_code,
        "message": str(exc),
        "type": type(exc).__name__,
        "recoverable": recoverable,
    }
    if how_to_fix:
        error_block["how_to_fix"] = how_to_fix

    response: Dict[str, Any] = {
        "status": "error",
        "tool": tool,
        "intent": intent,
        "timestamp": _timestamp(),
        "error": error_block,
    }
    if context:
        response["context"] = context

    # Structured error logging for observability
    logger.error(
        "Tool error occurred",
        extra={
            "tool": tool,
            "intent": intent,
            "error_code": error_code,
            "recoverable": recoverable,
            "error_type": type(exc).__name__,
        },
        exc_info=True,
    )

    return json.dumps(response, indent=2, ensure_ascii=False)
