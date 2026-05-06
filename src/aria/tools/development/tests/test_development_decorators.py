"""
Tests for development decorators module.

This module tests the decorators used for error handling and input validation
in Python runner operations.
"""

from unittest.mock import patch

import pytest

from aria.tools.development.decorators import (
    with_input_validation,
    with_runner_error_handling,
)
from aria.tools.development.exceptions import (
    PythonExecutionError,
    PythonExecutionTimeoutError,
    PythonRunnerError,
    PythonSecurityError,
    PythonSyntaxValidationError,
)


class TestWithRunnerErrorHandling:
    """Test suite for with_runner_error_handling decorator."""

    def test_security_error_handling(self):
        """Test handling of PythonSecurityError."""

        @with_runner_error_handling("test_operation")
        def security_violation(code: str) -> str:
            raise PythonSecurityError("Restricted operation detected")

        result = security_violation("import os")
        assert "error" in result.lower()
        assert "security" in result.lower() or "restricted" in result.lower()

    def test_syntax_validation_error_handling(self):
        """Test handling of PythonSyntaxValidationError."""

        @with_runner_error_handling("test_operation")
        def syntax_error(code: str) -> str:
            raise PythonSyntaxValidationError("Invalid syntax")

        result = syntax_error("def invalid")
        assert "error" in result.lower()

    def test_execution_timeout_error_handling(self):
        """Test handling of PythonExecutionTimeoutError."""

        @with_runner_error_handling("test_operation")
        def timeout_error(code: str) -> str:
            raise PythonExecutionTimeoutError("Execution timed out")

        result = timeout_error("while True: pass")
        assert "error" in result.lower()

    def test_execution_error_handling(self):
        """Test handling of PythonExecutionError."""

        @with_runner_error_handling("test_operation")
        def execution_error(code: str) -> str:
            raise PythonExecutionError("Runtime error occurred")

        result = execution_error("1/0")
        assert "error" in result.lower()

    def test_generic_runner_error_handling(self):
        """Test handling of generic PythonRunnerError."""

        @with_runner_error_handling("test_operation")
        def runner_error(code: str) -> str:
            raise PythonRunnerError("Generic runner error")

        result = runner_error("test")
        assert "error" in result.lower()

    def test_file_not_found_error_handling(self):
        """Test handling of FileNotFoundError."""

        @with_runner_error_handling("test_operation")
        def file_error(filename: str) -> str:
            raise FileNotFoundError("File not found")

        result = file_error("nonexistent.py")
        assert "error" in result.lower()

    def test_permission_error_handling(self):
        """Test handling of PermissionError."""

        @with_runner_error_handling("test_operation")
        def permission_error(filename: str) -> str:
            raise PermissionError("Permission denied")

        result = permission_error("protected.py")
        assert "error" in result.lower()

    def test_os_error_handling(self):
        """Test handling of OSError."""

        @with_runner_error_handling("test_operation")
        def os_error(filename: str) -> str:
            raise OSError("OS error occurred")

        result = os_error("test.py")
        assert "error" in result.lower()

    def test_unexpected_exception_handling(self):
        """Test handling of unexpected exceptions."""

        @with_runner_error_handling("test_operation")
        def unexpected_error(code: str) -> str:
            raise RuntimeError("Unexpected error")

        result = unexpected_error("test")
        assert "error" in result.lower()

    def test_no_args_function(self):
        """Test decorator with function that has no arguments."""

        @with_runner_error_handling("test_operation")
        def no_args_func() -> str:
            raise ValueError("Error with no args")

        result = no_args_func()
        assert "error" in result.lower()

    def test_multiple_args_function(self):
        """Test decorator with function that has multiple arguments."""

        @with_runner_error_handling("test_operation")
        def multi_args_func(code: str, timeout: int, verbose: bool) -> str:
            raise ValueError("Error with multiple args")

        result = multi_args_func("test", 30, True)
        assert "error" in result.lower()

    def test_kwargs_function(self):
        """Test decorator with function called with keyword arguments."""

        @with_runner_error_handling("test_operation")
        def kwargs_func(code: str, timeout: int = 30) -> str:
            raise ValueError("Error with kwargs")

        result = kwargs_func(code="test", timeout=60)
        assert "error" in result.lower()

    @patch("aria.tools.development.decorators.logger")
    def test_logging_on_security_error(self, mock_logger):
        """Test that security errors are logged with warning level."""

        @with_runner_error_handling("test_operation")
        def security_func(code: str) -> str:
            raise PythonSecurityError("Security violation")

        security_func("malicious code")
        mock_logger.warning.assert_called()

    @patch("aria.tools.development.decorators.logger")
    def test_logging_on_syntax_error(self, mock_logger):
        """Test that syntax errors are logged with warning level."""

        @with_runner_error_handling("test_operation")
        def syntax_func(code: str) -> str:
            raise PythonSyntaxValidationError("Syntax error")

        syntax_func("invalid syntax")
        mock_logger.warning.assert_called()

    @patch("aria.tools.development.decorators.logger")
    def test_logging_on_timeout_error(self, mock_logger):
        """Test that timeout errors are logged with warning level."""

        @with_runner_error_handling("test_operation")
        def timeout_func(code: str) -> str:
            raise PythonExecutionTimeoutError("Timeout")

        timeout_func("slow code")
        mock_logger.warning.assert_called()

    @patch("aria.tools.development.decorators.logger")
    def test_logging_on_execution_error(self, mock_logger):
        """Test that execution errors are logged with error level."""

        @with_runner_error_handling("test_operation")
        def exec_func(code: str) -> str:
            raise PythonExecutionError("Execution failed")

        exec_func("failing code")
        mock_logger.error.assert_called()

    @patch("aria.tools.development.decorators.logger")
    def test_logging_on_unexpected_error(self, mock_logger):
        """Test that unexpected errors are logged with exception level."""

        @with_runner_error_handling("test_operation")
        def unexpected_func(code: str) -> str:
            raise RuntimeError("Unexpected")

        unexpected_func("test")
        mock_logger.exception.assert_called()


class TestWithInputValidation:
    """Test suite for with_input_validation decorator."""

    def test_successful_validation(self):
        """Test decorator with valid inputs."""

        @with_input_validation(code=True, timeout=True)
        def validated_func(code: str, timeout: int) -> str:
            return f"Executed: {code} with timeout {timeout}"

        result = validated_func("print('hello')", 30)
        assert "Executed" in result

    def test_validation_with_none_values(self):
        """Test that None values are not validated."""

        @with_input_validation(code=True, timeout=True)
        def func_with_none(code: str | None = None, timeout: int | None = None) -> str:
            return "Success"

        # Should not raise even though values are None
        result = func_with_none(code=None, timeout=None)
        assert result == "Success"

    def test_validation_skipped_for_missing_params(self):
        """Test validation skipped for params not in function signature."""

        @with_input_validation(code=True, nonexistent=True)
        def simple_func(code: str) -> str:
            return "Success"

        result = simple_func("print('test')")
        assert result == "Success"

    def test_validation_with_defaults(self):
        """Test validation with default parameter values."""

        @with_input_validation(code=True, timeout=True)
        def func_with_defaults(code: str, timeout: int = 30) -> str:
            return f"Code: {code}, Timeout: {timeout}"

        result = func_with_defaults("print('test')")
        assert "Code: print('test')" in result

    def test_validation_with_kwargs(self):
        """Test validation when function is called with keyword arguments."""

        @with_input_validation(code=True, timeout=True)
        def kwargs_func(code: str, timeout: int) -> str:
            return "Success"

        result = kwargs_func(code="test", timeout=30)
        assert result == "Success"

    def test_validation_with_mixed_args_kwargs(self):
        """Test validation with mixed positional and keyword arguments."""

        @with_input_validation(code=True, timeout=True)
        def mixed_func(code: str, timeout: int, verbose: bool = False) -> str:
            return "Success"

        result = mixed_func("test", timeout=30, verbose=True)
        assert result == "Success"

    def test_validation_disabled_for_param(self):
        """Test that validation can be disabled for specific parameters."""

        @with_input_validation(code=True, timeout=False)
        def selective_func(code: str, timeout: int) -> str:
            return "Success"

        result = selective_func("test", 30)
        assert result == "Success"

    def test_validation_with_large_code(self):
        """Test that extremely large code raises validation error."""

        @with_input_validation(code=True)
        def code_func(code: str) -> str:
            return "Success"

        # Code exceeding 10MB should raise error
        from aria.tools.development.exceptions import PythonSecurityError

        with pytest.raises(PythonSecurityError):
            code_func("x" * 10_000_001)  # Exceeds 10MB limit

    def test_validation_with_no_params(self):
        """Test decorator with no validation parameters."""

        @with_input_validation()
        def no_validation_func(code: str) -> str:
            return "Success"

        result = no_validation_func("test")
        assert result == "Success"

    def test_validation_preserves_function_metadata(self):
        """Test that decorator preserves function name and docstring."""

        @with_input_validation(code=True)
        def documented_func(code: str) -> str:
            """This is a documented function."""
            return "Success"

        assert documented_func.__name__ == "documented_func"
        assert documented_func.__doc__ == "This is a documented function."

    def test_chained_decorators(self):
        """Test that decorators can be chained together."""

        @with_runner_error_handling("test_op")
        @with_input_validation(code=True)
        def chained_func(code: str) -> str:
            if "error" in code:
                raise ValueError("Error in code")
            return f"Success: {code}"

        result = chained_func("print('test')")
        assert "Success" in result

        # Test error path through both decorators
        result = chained_func("error code")
        assert "error" in result.lower()

    def test_validation_with_complex_signature(self):
        """Test validation with complex function signature."""

        @with_input_validation(code=True, filename=True)
        def complex_func(
            code: str,
            filename: str = "test.py",
            timeout: int = 30,
            capture_output: bool = True,
        ) -> str:
            return "Success"

        result = complex_func("test", "script.py")
        assert result == "Success"

    @patch("aria.tools.development.decorators._validate_inputs")
    def test_validate_inputs_called_correctly(self, mock_validate):
        """Test that _validate_inputs is called with correct parameters."""

        @with_input_validation(code=True, timeout=True)
        def test_func(code: str, timeout: int) -> str:
            return "Success"

        test_func("print('test')", 30)
        mock_validate.assert_called_once_with(code="print('test')", timeout=30)

    @patch("aria.tools.development.decorators._validate_inputs")
    def test_validate_inputs_not_called_when_no_params(self, mock_validate):
        """Test _validate_inputs not called when no params to validate."""

        @with_input_validation(code=False, timeout=False)
        def test_func(code: str, timeout: int) -> str:
            return "Success"

        test_func("test", 30)
        mock_validate.assert_not_called()

    def test_validation_with_positional_only_args(self):
        """Test validation with positional-only arguments."""

        @with_input_validation(code=True)
        def positional_func(code: str, /, timeout: int = 30) -> str:
            return "Success"

        result = positional_func("test", 60)
        assert result == "Success"

    def test_validation_with_keyword_only_args(self):
        """Test validation with keyword-only arguments."""

        @with_input_validation(code=True, timeout=True)
        def keyword_func(code: str, *, timeout: int = 30) -> str:
            return "Success"

        result = keyword_func("test", timeout=60)
        assert result == "Success"

    def test_async_function_compatibility(self):
        """Test decorator with async functions (metadata preservation)."""

        @with_input_validation(code=True)
        async def async_func(code: str) -> str:
            """Async function."""
            return "Success"

        # Just verify the decorator doesn't break the function
        assert async_func.__name__ == "async_func"
        assert async_func.__doc__ and "Async function" in async_func.__doc__

    def test_class_method_decoration(self):
        """Test decorator on class methods."""

        class TestClass:
            @with_input_validation(code=True)
            def method(self, code: str) -> str:
                return f"Method: {code}"

        obj = TestClass()
        result = obj.method("test")
        assert "Method: test" in result

    @staticmethod
    def test_static_method_decoration():
        """Test decorator on static methods."""

        class TestClass:
            @staticmethod
            @with_input_validation(code=True)
            def static_method(code: str) -> str:
                return f"Static: {code}"

        result = TestClass.static_method("test")
        assert "Static: test" in result

    def test_class_method_with_classmethod_decorator(self):
        """Test decorator on class methods with @classmethod."""

        class TestClass:
            @classmethod
            @with_input_validation(code=True)
            def class_method(cls, code: str) -> str:
                return f"Class: {code}"

        result = TestClass.class_method("test")
        assert "Class: test" in result
