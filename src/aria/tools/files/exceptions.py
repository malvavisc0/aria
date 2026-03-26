"""
Custom exceptions for file operations.

This module defines specific exceptions used throughout the file operations
system to provide clear error information and proper exception handling.
"""

from aria.tools.errors import ToolError


class FileSecurityError(ToolError):
    """Raised when file operation violates security constraints."""

    code = "SECURITY_VIOLATION"
    recoverable = False
    how_to_fix = "Avoid using symlinks or restricted file types."


class FileOperationError(ToolError):
    """Raised when file operation fails."""

    code = "OPERATION_FAILED"
    recoverable = True
    how_to_fix = "Check file permissions and try again."


class ToolFileNotFoundError(FileOperationError):
    """File not found."""

    code = "FILE_NOT_FOUND"
    how_to_fix = "Verify the file path exists. Use list_directory to check available files."


class ToolPermissionDeniedError(FileOperationError):
    """Permission denied for file operation."""

    code = "PERMISSION_DENIED"
    how_to_fix = "Check file permissions or run with appropriate privileges."


class PathTraversalError(FileSecurityError):
    """Path traversal attempt detected."""

    code = "PATH_TRAVERSAL_BLOCKED"
    how_to_fix = (
        "Use paths within allowed directories. Do not use '..' in paths."
    )
