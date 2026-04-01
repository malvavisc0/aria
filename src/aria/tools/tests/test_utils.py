"""Tests for shared utility functions in utils.py."""

import json
from datetime import datetime, timezone

from aria.tools import (
    safe_json,
    tool_error_response,
    tool_response,
    tool_success_response,
    utc_timestamp,
)


class TestUtcTimestamp:
    """Tests for utc_timestamp() function."""

    def test_returns_iso_format(self):
        """Timestamp should be in ISO 8601 format."""
        result = utc_timestamp()
        # Should parse without error
        parsed = datetime.fromisoformat(result)
        assert parsed is not None

    def test_returns_utc_timezone(self):
        """Timestamp should be in UTC timezone."""
        result = utc_timestamp()
        parsed = datetime.fromisoformat(result)
        assert parsed.tzinfo == timezone.utc

    def test_returns_string(self):
        """Timestamp should be a string."""
        result = utc_timestamp()
        assert isinstance(result, str)


class TestSafeJson:
    """Tests for safe_json() function."""

    def test_serializes_simple_dict(self):
        """Should serialize a simple dictionary."""
        data = {"key": "value", "number": 42}
        result = safe_json(data)
        parsed = json.loads(result)
        assert parsed == data

    def test_serializes_nested_dict(self):
        """Should serialize nested dictionaries."""
        data = {"outer": {"inner": "value", "list": [1, 2, 3]}}
        result = safe_json(data)
        parsed = json.loads(result)
        assert parsed == data

    def test_handles_non_serializable_objects(self):
        """Should handle non-serializable objects with default handler."""
        data = {"date": datetime(2024, 1, 1, 12, 0, 0)}
        result = safe_json(data)
        parsed = json.loads(result)
        # Should convert datetime to string
        assert "date" in parsed

    def test_custom_default_handler(self):
        """Should use custom default handler when provided."""
        data = {"obj": object()}

        def custom_handler(obj):
            return f"<custom:{type(obj).__name__}>"

        result = safe_json(data, default=custom_handler)
        parsed = json.loads(result)
        assert "<custom:object>" in parsed["obj"]

    def test_compact_output(self):
        """Should produce compact output when indent=None."""
        data = {"key": "value"}
        result = safe_json(data, indent=None)
        assert "\n" not in result

    def test_ensure_ascii_true(self):
        """Should escape non-ASCII when ensure_ascii=True."""
        data = {"message": "héllo"}
        result = safe_json(data, ensure_ascii=True)
        # Unicode characters should be escaped
        assert "\\u00e9" in result

    def test_ensure_ascii_false(self):
        """Should preserve non-ASCII when ensure_ascii=False."""
        data = {"message": "héllo"}
        result = safe_json(data, ensure_ascii=False)
        parsed = json.loads(result)
        assert parsed["message"] == "héllo"


class TestToolSuccessResponse:
    """Tests for tool_success_response() function."""

    def test_basic_success_response(self):
        """Should create a basic success response."""
        result = tool_success_response(
            tool="test_tool",
            reason="test reason",
            data={"result": "success"},
        )
        parsed = json.loads(result)

        assert parsed["status"] == "success"
        assert parsed["tool"] == "test_tool"
        assert parsed["reason"] == "test reason"
        assert parsed["data"] == {"result": "success"}
        assert "timestamp" in parsed

    def test_includes_context(self):
        """Should include additional context fields."""
        result = tool_success_response(
            tool="test_tool",
            reason="test reason",
            data={"result": "success"},
            extra_field="extra_value",
        )
        parsed = json.loads(result)

        assert parsed["context"]["extra_field"] == "extra_value"

    def test_handles_empty_reason(self):
        """Should handle empty reason with fallback."""
        result = tool_success_response(
            tool="test_tool",
            reason="",
            data={"result": "success"},
        )
        parsed = json.loads(result)

        assert "unspecified_test_tool_operation" in parsed["reason"]

    def test_handles_whitespace_reason(self):
        """Should handle whitespace-only reason with fallback."""
        result = tool_success_response(
            tool="test_tool",
            reason="   ",
            data={"result": "success"},
        )
        parsed = json.loads(result)

        assert "unspecified_test_tool_operation" in parsed["reason"]

    def test_timestamp_is_utc(self):
        """Timestamp should be in UTC."""
        result = tool_success_response(
            tool="test_tool",
            reason="test reason",
            data={},
        )
        parsed = json.loads(result)

        parsed_time = datetime.fromisoformat(parsed["timestamp"])
        assert parsed_time.tzinfo == timezone.utc


class TestToolErrorResponse:
    """Tests for tool_error_response() function."""

    def test_basic_error_response(self):
        """Should create a basic error response."""

        class TestError(Exception):
            code = "TEST_ERROR"
            recoverable = True
            how_to_fix = "Fix it"

        exc = TestError("Test error message")
        result = tool_error_response(
            tool="test_tool",
            reason="test reason",
            exc=exc,
        )
        parsed = json.loads(result)

        assert parsed["status"] == "error"
        assert parsed["tool"] == "test_tool"
        assert parsed["reason"] == "test reason"
        assert parsed["error"]["code"] == "TEST_ERROR"
        assert parsed["error"]["message"] == "Test error message"
        assert parsed["error"]["recoverable"] is True
        assert parsed["error"]["how_to_fix"] == "Fix it"
        assert "timestamp" in parsed

    def test_error_without_custom_attributes(self):
        """Should handle exceptions without custom attributes."""
        exc = ValueError("Simple error")
        result = tool_error_response(
            tool="test_tool",
            reason="test reason",
            exc=exc,
        )
        parsed = json.loads(result)

        assert parsed["status"] == "error"
        assert parsed["error"]["code"] == "VALUEERROR"
        assert parsed["error"]["recoverable"] is False

    def test_includes_context(self):
        """Should include additional context fields."""
        exc = ValueError("Error")
        result = tool_error_response(
            tool="test_tool",
            reason="test reason",
            exc=exc,
            extra_field="extra_value",
        )
        parsed = json.loads(result)

        assert parsed["context"]["extra_field"] == "extra_value"


class TestToolResponse:
    """Tests for tool_response() convenience function."""

    def test_returns_success_when_no_exception(self):
        """Should return success response when no exception provided."""
        result = tool_response(
            tool="test_tool",
            reason="test reason",
            data={"result": "success"},
        )
        parsed = json.loads(result)

        assert parsed["status"] == "success"
        assert parsed["data"] == {"result": "success"}

    def test_returns_error_when_exception_provided(self):
        """Should return error response when exception provided."""
        exc = ValueError("Error occurred")
        result = tool_response(
            tool="test_tool",
            reason="test reason",
            exc=exc,
        )
        parsed = json.loads(result)

        assert parsed["status"] == "error"
        assert "Error occurred" in parsed["error"]["message"]

    def test_uses_empty_dict_when_data_none(self):
        """Should use empty dict for data when None is provided."""
        result = tool_response(
            tool="test_tool",
            reason="test reason",
            data=None,
        )
        parsed = json.loads(result)

        assert parsed["status"] == "success"
        assert parsed["data"] == {}
