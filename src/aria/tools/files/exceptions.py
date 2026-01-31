"""
Custom exceptions for file operations.

This module defines specific exceptions used throughout the file operations
system to provide clear error information and proper exception handling.
"""


class FileSecurityError(Exception):
    """Raised when file operation violates security constraints."""

    pass


class FileOperationError(Exception):
    """Raised when file operation fails."""

    pass
