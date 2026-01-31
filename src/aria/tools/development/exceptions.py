"""
Custom exceptions for Python code execution and validation.

This module defines specific exceptions used throughout the Python runner
system to provide clear error information and proper exception handling.
"""


class PythonRunnerError(Exception):
    """Base exception for Python runner operations."""

    pass


class PythonSyntaxValidationError(PythonRunnerError):
    """Raised when Python syntax validation fails."""

    pass


class PythonExecutionError(PythonRunnerError):
    """Raised when Python code execution fails."""

    pass


class PythonExecutionTimeoutError(PythonRunnerError):
    """Raised when Python code execution exceeds timeout limit."""

    pass


class PythonSecurityError(PythonRunnerError):
    """Raised when code attempts to violate security restrictions."""

    pass
