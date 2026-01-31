"""
Tests for file operation decorators.

This module tests the decorators used in file operations, focusing on
error handling and input validation edge cases.
"""

from aria.tools.files.decorators import (
    with_file_operation_error_handling,
    with_input_validation,
)
from aria.tools.files.exceptions import FileOperationError, FileSecurityError


class TestWithFileOperationErrorHandling:
    """Test suite for with_file_operation_error_handling decorator."""

    def test_decorator_handles_oserror(self):
        """Test that decorator converts OSError to an error response."""

        @with_file_operation_error_handling("test_operation")
        def function_that_raises_oserror(intent: str, file_name: str):
            raise OSError("Permission denied")

        result = function_that_raises_oserror("test", "test.txt")
        assert isinstance(result, str)
        assert "Permission" in result or "denied" in result.lower()

    def test_decorator_handles_generic_exception(self):
        """Test decorator converts generic Exception to error response."""

        @with_file_operation_error_handling("test_operation")
        def function_that_raises_generic_exception(
            intent: str, file_name: str
        ):
            raise ValueError("Unexpected error")

        result = function_that_raises_generic_exception("test", "test.txt")
        assert isinstance(result, str)
        assert "Unexpected error" in result

    def test_decorator_handles_file_security_error(self):
        """Test decorator converts FileSecurityError to error response."""

        @with_file_operation_error_handling("test_operation")
        def function_that_raises_security_error(intent: str, file_name: str):
            raise FileSecurityError("Security violation")

        result = function_that_raises_security_error("test", "test.txt")
        assert isinstance(result, str)
        assert "Security" in result

    def test_decorator_reraises_file_operation_error(self):
        """Test decorator returns error response for FileOperationError."""

        @with_file_operation_error_handling("test_operation")
        def function_that_raises_file_operation_error(
            intent: str, file_name: str
        ):
            raise FileOperationError("Operation failed")

        result = function_that_raises_file_operation_error("test", "test.txt")
        assert isinstance(result, str)
        assert "Operation failed" in result

    def test_decorator_successful_execution(self):
        """Test that decorator allows successful execution."""

        @with_file_operation_error_handling("test_operation")
        def successful_function(intent: str, file_name: str):
            return f"Success: {file_name}"

        result = successful_function("test", "test.txt")
        assert result == "Success: test.txt"

    def test_decorator_with_no_args(self):
        """Test decorator with function that has no args (no raise)."""

        @with_file_operation_error_handling("test_operation")
        def function_with_no_args():
            raise OSError("No file specified")

        result = function_with_no_args()
        assert isinstance(result, str)
        assert "error" in result

    def test_decorator_with_kwargs(self):
        """Test decorator with function called using kwargs (no raise)."""

        @with_file_operation_error_handling("test_operation")
        def function_with_kwargs(intent: str, file_name: str, content: str):
            raise OSError("Write failed")

        result = function_with_kwargs(
            reason="test",
            file_name="test.txt",
            content="data",
        )
        assert isinstance(result, str)
        assert "error" in result


class TestWithInputValidation:
    """Test suite for with_input_validation decorator."""

    def test_decorator_validates_file_name(self):
        """Test that decorator validates file_name parameter."""

        @with_input_validation()
        def function_with_file_name(file_name):
            return f"Processing: {file_name}"

        # Valid file name should work
        result = function_with_file_name("test.txt")
        assert result == "Processing: test.txt"

    def test_decorator_with_validation_params(self):
        """Test decorator with specific validation parameters."""

        @with_input_validation(contents=True)
        def function_with_contents(file_name, contents):
            return f"Writing {len(contents)} bytes to {file_name}"

        result = function_with_contents("test.txt", "Hello World")
        assert "Writing 11 bytes" in result

    def test_decorator_skips_none_values(self):
        """Test that decorator skips validation for None values."""

        @with_input_validation(contents=True, offset=True)
        def function_with_optional_params(
            file_name, contents=None, offset=None
        ):
            return f"File: {file_name}"

        # Should not raise error even though contents and offset are None
        result = function_with_optional_params("test.txt")
        assert result == "File: test.txt"

    def test_decorator_converts_security_error_to_operation_error(self):
        """Test decorator converts FileSecurityError to error response."""
        from unittest.mock import patch

        @with_input_validation()
        def function_to_test(file_name):
            return "Success"

        # Mock _validate_inputs to raise FileSecurityError
        with patch(
            "aria.tools.files.decorators._validate_inputs",
            side_effect=FileSecurityError("Invalid path"),
        ):
            result = function_to_test("../invalid.txt")
            assert isinstance(result, str)
            assert "Invalid path" in result

    def test_decorator_with_multiple_validation_params(self):
        """Test decorator with multiple validation parameters."""

        @with_input_validation(contents=True, chunk_size=True, offset=True)
        def complex_function(file_name, contents, chunk_size, offset):
            return f"File: {file_name}, Size: {chunk_size}, Offset: {offset}"

        result = complex_function("test.txt", "data", 100, 0)
        assert "File: test.txt" in result
        assert "Size: 100" in result
        assert "Offset: 0" in result

    def test_decorator_with_defaults(self):
        """Test decorator with function that has default parameter values."""

        @with_input_validation(chunk_size=True)
        def function_with_defaults(file_name, chunk_size=1000):
            return f"Chunk size: {chunk_size}"

        result = function_with_defaults("test.txt")
        assert result == "Chunk size: 1000"

    def test_decorator_preserves_function_metadata(self):
        """Test that decorator preserves original function metadata."""

        @with_input_validation()
        def documented_function(file_name):
            """This is a documented function."""
            return file_name

        assert documented_function.__name__ == "documented_function"
        assert documented_function.__doc__ == "This is a documented function."

    def test_error_handling_decorator_preserves_metadata(self):
        """Test that error handling decorator preserves function metadata."""

        @with_file_operation_error_handling("test_op")
        def documented_function(file_name):
            """This is a documented function."""
            return file_name

        assert documented_function.__name__ == "documented_function"
        assert documented_function.__doc__ == "This is a documented function."

    def test_decorator_with_false_validation_params(self):
        """Test decorator ignores parameters with False validation flag."""

        @with_input_validation(contents=False, chunk_size=True)
        def selective_validation(file_name, contents, chunk_size):
            return f"Validated chunk_size: {chunk_size}"

        # Should validate chunk_size but not contents
        result = selective_validation("test.txt", "any content", 500)
        assert "Validated chunk_size: 500" in result
