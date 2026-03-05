"""Shared test utilities for tool error handling."""

import json
from typing import Any, Dict, Optional


def assert_error_response(
    response: str,
    expected_tool: Optional[str] = None,
    expected_intent: Optional[str] = None,
    expected_code: Optional[str] = None,
    expected_recoverable: Optional[bool] = None,
) -> Dict[str, Any]:
    """Validate that a tool response is a properly formatted error.

    Args:
        response: JSON string response from a tool
        expected_tool: Expected tool name (optional)
        expected_intent: Expected intent value (optional)
        expected_code: Expected error code (optional)
        expected_recoverable: Expected recoverable value (optional)

    Returns:
        Parsed response dict for further assertions

    Raises:
        AssertionError: If any validation fails
    """
    result = json.loads(response)

    # Top-level structure
    assert (
        result["status"] == "error"
    ), f"Expected status='error', got {result.get('status')}"

    # Required fields
    assert "tool" in result, "Missing 'tool' field"
    assert "intent" in result, "Missing 'intent' field"
    assert "timestamp" in result, "Missing 'timestamp' field"
    assert "error" in result, "Missing 'error' field"

    # Error block structure
    error = result["error"]
    assert "code" in error, "Missing error.code"
    assert "message" in error, "Missing error.message"
    assert "recoverable" in error, "Missing error.recoverable"
    assert "how_to_fix" in error, "Missing error.how_to_fix"

    # Optional validations
    if expected_tool:
        assert (
            result["tool"] == expected_tool
        ), f"Expected tool={expected_tool}"
    if expected_intent:
        assert (
            result["intent"] == expected_intent
        ), f"Expected intent={expected_intent}"
    if expected_code:
        assert error["code"] == expected_code, f"Expected code={expected_code}"
    if expected_recoverable is not None:
        assert (
            error["recoverable"] == expected_recoverable
        ), f"Expected recoverable={expected_recoverable}"

    return result
