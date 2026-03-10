"""
Custom exceptions for Python code execution and validation.

This module defines specific exceptions used throughout the Python runner
system to provide clear error information and proper exception handling.
"""

from aria.tools.errors import ToolError


class PythonRunnerError(ToolError):
    """Base exception for Python runner operations."""

    code = "PYTHON_RUNNER_ERROR"
    recoverable = False
    how_to_fix = "Check the Python code and try again."


class PythonSyntaxValidationError(PythonRunnerError):
    """Raised when Python syntax validation fails."""

    code = "SYNTAX_ERROR"
    recoverable = True
    how_to_fix = "Fix the syntax error in the Python code and retry."


class PythonExecutionError(PythonRunnerError):
    """Raised when Python code execution fails."""

    code = "EXECUTION_ERROR"
    recoverable = True
    how_to_fix = "Check the error output and fix the code."


class PythonExecutionTimeoutError(PythonRunnerError):
    """Raised when Python code execution exceeds timeout limit."""

    code = "EXECUTION_TIMEOUT"
    recoverable = True
    how_to_fix = "Optimize code or increase timeout parameter."


class PythonSecurityError(PythonRunnerError):
    """Raised when code attempts to violate security restrictions."""

    code = "SECURITY_VIOLATION"
    recoverable = False
    how_to_fix = "Remove restricted operations (imports, builtins) from code."
