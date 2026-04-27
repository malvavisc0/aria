"""Response builders for file operations.

This module provides standardized response helpers for file tool operations,
ensuring consistent output format using the Standard Envelope pattern.
"""

from typing import Any, Dict

from aria.tools import get_function_name, tool_error_response, tool_response


def file_success_response(reason: str, data: Dict[str, Any], tool: str = "") -> str:
    """Build standardized success response for file operations.

    Args:
        reason: The agent's stated reason for calling this tool.
        data: The response data payload.
        tool: Tool name (if empty, uses get_function_name).

    Returns:
        JSON string with standardized success format.
    """
    if not tool:
        tool = get_function_name(depth=2)
    return tool_response(
        tool=tool,
        reason=reason,
        data=data,
    )


def file_error_response(reason: str, exc: Exception) -> str:
    """Build standardized error response for file operations.

    Args:
        reason: The agent's stated reason for calling this tool.
        exc: The exception that occurred.

    Returns:
        JSON string with standardized error format.
    """
    return tool_error_response(
        tool=get_function_name(),
        reason=reason,
        exc=exc,
    )
