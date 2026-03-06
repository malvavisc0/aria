"""
Internal helper functions for file operations.

This module contains private helper functions used by the main file operations
module. These functions should not be imported directly by external modules.
"""

import shutil
import stat
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from aria.tools import safe_json, tool_error_response, utc_timestamp
from aria.tools.constants import BASE_DIR, MAX_FILE_SIZE
from aria.tools.files.constants import (
    ALLOWED_EXTENSIONS,
    BLOCKED_PATTERNS,
    MAX_CHUNK_SIZE,
    MAX_LINE_LENGTH,
)
from aria.tools.files.exceptions import FileOperationError, FileSecurityError

# Re-export shared utilities for backward compatibility
_timestamp = utc_timestamp
_safe_json = safe_json


def _error_response(
    operation: str,
    file_name: str,
    exc: Exception,
    intent: str = "",
) -> str:
    """Generate secure error response without information disclosure.

    Args:
        operation: The operation that failed
        file_name: The file name involved in the operation
        exc: The exception that occurred
        intent: The agent's stated intent for calling this tool

    Returns:
        str: JSON formatted error response
    """
    # Extract error metadata from exception
    error_code = getattr(exc, "code", type(exc).__name__.upper())
    recoverable = getattr(exc, "recoverable", False)
    how_to_fix = getattr(exc, "how_to_fix", None)

    if isinstance(exc, FileSecurityError):
        error_msg = f"Security validation failed: {str(exc)}"
        logger.warning(f"Security validation failed for {file_name}: {exc}")
    elif isinstance(exc, FileOperationError):
        error_msg = f"File operation failed: {str(exc)}"
        logger.error(f"File operation failed for {file_name}: {exc}")
    elif isinstance(exc, (OSError, PermissionError)):
        error_msg = "File access denied or not found"
        logger.warning(f"File access denied for {file_name}")
    else:
        error_msg = f"Unexpected error: {str(exc)}"
        logger.error(f"Unexpected error for {file_name}: {exc}")

    # Build error block with standard fields
    error_block = {
        "code": error_code,
        "message": error_msg,
        "type": type(exc).__name__,
        "recoverable": recoverable,
    }
    if how_to_fix:
        error_block["how_to_fix"] = how_to_fix

    return _safe_json(
        {
            "status": "error",
            "tool": operation,
            "intent": intent,
            "timestamp": _timestamp(),
            "error": error_block,
            "context": {"file_name": file_name},
        }
    )


def _validate_inputs(
    file_name: str,
    chunk_size: int = 0,
    offset: int = 0,
    length: int = 0,
    contents: Optional[str] = None,
    new_lines: Optional[List[str]] = None,
) -> None:
    """Comprehensive input validation for file operations.

    Validates file name, size limits, and content parameters to prevent
    security vulnerabilities and resource exhaustion.

    Args:
        file_name: Name of the file to validate
        chunk_size: Size of chunks for operations (default: 0)
        offset: Offset for file operations (default: 0)
        length: Length of operations (default: 0)
        contents: File content to validate (default: None)
        new_lines: List of new lines to validate (default: None)

    Raises:
        FileSecurityError: If validation fails due to security violations
    """
    if not file_name or not isinstance(file_name, str):
        raise FileSecurityError("Invalid file name provided")

    # Check for path traversal attempts
    if ".." in file_name:
        raise FileSecurityError("Path traversal attempt detected in file name")

    # Check for blocked patterns
    if any(pattern in file_name for pattern in BLOCKED_PATTERNS):
        raise FileSecurityError("File name contains blocked patterns")

    # Validate numeric parameters
    if chunk_size > MAX_CHUNK_SIZE:
        raise FileSecurityError(
            f"chunk_size must be between 1 and {MAX_CHUNK_SIZE}"
        )

    if offset < 0 or length < 0:
        raise FileSecurityError("Negative offset or length not allowed")

    # Validate content size
    if contents:
        content_length = len(contents)
        if content_length > MAX_FILE_SIZE:
            raise FileSecurityError(
                f"Content size {content_length} exceeds limit: {MAX_FILE_SIZE}"
            )

    # Validate line lengths
    if new_lines:
        for line in new_lines:
            line_length = len(line)
            if line_length > MAX_LINE_LENGTH:
                raise FileSecurityError(
                    f"Line length {line_length} exceeds limit: {MAX_LINE_LENGTH}"
                )


def _count_lines_efficiently(file_path: Path) -> int:
    """Memory-efficient line counting for large files.

    Reads file in chunks to avoid loading entire file into memory.

    Args:
        file_path: Path to the file to count lines for

    Returns:
        int: Number of lines in the file

    Raises:
        FileOperationError: If path is a directory or file cannot be read
    """
    # Check if path is a directory
    if file_path.is_dir():
        raise FileOperationError(
            f"Path is a directory, not a file: {file_path}"
        )

    count = 0
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                count += chunk.count(b"\n")
        return count
    except OSError as exc:
        raise FileOperationError(
            f"Failed to read file for line counting: {exc}"
        ) from exc


def _secure_resolve_path(file_name: str, check_exists: bool = True) -> Path:
    """Secure path resolution with comprehensive validation.

    Resolves file path while preventing path traversal attacks and validating
    file type restrictions. Only accepts absolute paths.

    Args:
        file_name: Absolute path (e.g., /home/user/data/downloads/file.txt)
        check_exists: Whether to check if file exists (default: True)

    Returns:
        Path: Resolved absolute path to the file

    Raises:
        FileSecurityError: If path resolution fails due to security violations
        FileOperationError: If path is a directory or not absolute
    """
    try:
        # Resolve BASE_DIR to handle symlinks (e.g., /var -> /private/var on macOS)
        base_dir_resolved = BASE_DIR.resolve()

        # Only accept absolute paths
        file_path = Path(file_name)
        if not file_path.is_absolute():
            raise FileOperationError(f"Path must be absolute: {file_name}")

        # Check for symlinks BEFORE resolving (to detect symlinked files)
        if file_path.is_symlink():
            raise FileSecurityError("Symlinks not allowed")

        # Resolve the absolute path
        file_path = file_path.resolve()

        # Check for path traversal attacks - path must be within BASE_DIR
        if not str(file_path).startswith(str(base_dir_resolved)):
            raise FileSecurityError("Path traversal attempt detected")

        # Check if path is a directory
        if file_path.is_dir():
            raise FileOperationError(
                f"Path is a directory, not a file: {file_name}"
            )

        # Check file extension (only if it has an extension)
        if (
            file_path.suffix
            and file_path.suffix.lower() not in ALLOWED_EXTENSIONS
        ):
            msg = f"File type not allowed: {file_path.suffix}"
            raise FileSecurityError(msg)

        # Check if file exists if required
        if check_exists and not file_path.exists():
            raise FileOperationError(f"File not found: {file_name}")

        return file_path
    except (FileSecurityError, FileOperationError):
        raise
    except Exception as exc:
        raise FileSecurityError(f"Path resolution failed: {exc}") from exc


def _secure_resolve_dir(dir_name: str) -> Path:
    """Secure directory path resolution.

    Args:
        dir_name: Name of the directory to resolve

    Returns:
        Path: Resolved absolute path to the directory

    Raises:
        FileSecurityError: If path resolution fails
    """
    try:
        # Resolve BASE_DIR to handle symlinks (e.g., /var -> /private/var on macOS)
        base_dir_resolved = BASE_DIR.resolve()

        dir_path = (BASE_DIR / dir_name).resolve()

        if not str(dir_path).startswith(str(base_dir_resolved)):
            raise FileSecurityError("Path traversal attempt detected")

        if dir_path.is_symlink():
            raise FileSecurityError("Symlinks not allowed")

        return dir_path
    except FileSecurityError:
        raise
    except Exception as exc:
        raise FileSecurityError(f"Path resolution failed: {exc}") from exc


def _read_lines_streaming(
    file_path: Path, offset: int, length: int
) -> List[str]:
    """Read lines from file using streaming.

    Args:
        file_path: Path to the file
        offset: Starting line number (0-indexed)
        length: Number of lines to read (0 = read all remaining)

    Returns:
        List[str]: Lines read from file (without newline characters)
    """
    lines = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i < offset:
                    continue
                if length > 0 and i >= offset + length:
                    break
                lines.append(line.rstrip("\n\r"))
        return lines
    except OSError as exc:
        raise FileOperationError(f"Failed to read file: {exc}") from exc


def _modify_lines_streaming(
    file_path: Path,
    offset: int,
    length: int,
    new_lines: Optional[List[str]] = None,
) -> tuple[int, int]:
    """Modify lines in file using streaming to avoid loading entire file.

    Args:
        file_path: Path to the file
        offset: Starting line number (0-indexed)
        length: Number of lines to replace/delete
        new_lines: New lines to insert (None for delete operation)

    Returns:
        tuple: (old_total_lines, new_total_lines)
    """
    temp_path = file_path.with_suffix(file_path.suffix + ".tmp")
    old_total_lines = 0
    new_total_lines = 0

    try:
        with (
            open(file_path, "r", encoding="utf-8") as infile,
            open(temp_path, "w", encoding="utf-8") as outfile,
        ):
            for i, line in enumerate(infile):
                old_total_lines += 1
                if i < offset:
                    outfile.write(line)
                    new_total_lines += 1
                elif i == offset:
                    # Insert new lines at offset position
                    if new_lines:
                        for new_line in new_lines:
                            outfile.write(new_line + "\n")
                            new_total_lines += 1
                    # If length > 0, skip this line (it's being replaced)
                    # If length == 0, write this line (pure insert)
                    if length == 0:
                        outfile.write(line)
                        new_total_lines += 1
                elif i < offset + length:
                    # Skip lines in the range to be replaced/deleted
                    pass
                else:
                    outfile.write(line)
                    new_total_lines += 1

            # If offset is at or beyond end of file, append new lines
            if offset >= old_total_lines and new_lines:
                for new_line in new_lines:
                    outfile.write(new_line + "\n")
                    new_total_lines += 1

        # Replace original file with modified file
        shutil.move(str(temp_path), str(file_path))
        return old_total_lines, new_total_lines

    except Exception as exc:
        # Clean up temp file if it exists
        try:
            if temp_path.exists():
                temp_path.unlink()
        except OSError:
            # Log but don't fail if cleanup fails
            logger.warning(f"Failed to clean up temp file: {temp_path}")
        raise FileOperationError(f"Failed to modify file: {exc}") from exc


def _atomic_write(file_path: Path, content: str) -> None:
    """Write file atomically using temp file and rename.

    Args:
        file_path: Path to the file to write
        content: Content to write to the file

    Raises:
        FileOperationError: If write operation fails
    """
    temp_path = file_path.with_suffix(file_path.suffix + ".tmp")
    try:
        # Write to temp file
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Atomic rename (on POSIX systems)
        shutil.move(str(temp_path), str(file_path))
    except Exception as exc:
        # Clean up temp file if it exists
        try:
            if temp_path.exists():
                temp_path.unlink()
        except OSError:
            logger.warning(f"Failed to clean up temp file: {temp_path}")
        raise FileOperationError(f"Failed to write file: {exc}") from exc


def _create_backup(file_path: Path) -> Optional[Path]:
    """Create backup of file before destructive operation.

    Args:
        file_path: Path to the file to backup

    Returns:
        Path to backup file, or None if backup failed
    """
    if not file_path.exists():
        return None

    backup_path = file_path.with_suffix(file_path.suffix + ".backup")
    try:
        shutil.copy2(file_path, backup_path)
        logger.info(f"Created backup: {backup_path}")
        return backup_path
    except Exception as exc:
        logger.warning(f"Failed to create backup for {file_path}: {exc}")
        return None


def _build_directory_tree(
    path: Path, current_depth: int, max_depth: int
) -> Dict[str, Any]:
    """Recursively build directory tree structure.

    Args:
        path: Path to build tree for
        current_depth: Current recursion depth
        max_depth: Maximum depth to traverse

    Returns:
        Dict: Tree structure with name, type, children, and size
    """
    tree = {"name": path.name or ".", "type": "directory", "children": []}

    if current_depth >= max_depth:
        return tree

    try:
        for item in sorted(path.iterdir()):
            if item.is_file():
                tree["children"].append(
                    {
                        "name": item.name,
                        "type": "file",
                        "size": item.stat().st_size,
                    }
                )
            elif item.is_dir() and not item.is_symlink():
                tree["children"].append(
                    _build_directory_tree(item, current_depth + 1, max_depth)
                )
    except PermissionError:
        pass

    return tree


def _count_tree_items(tree: Dict[str, Any]) -> tuple[int, int]:
    """Count total files and directories in tree.

    Args:
        tree: Tree structure from _build_directory_tree

    Returns:
        tuple: (total_files, total_directories)
    """
    files = 0
    dirs = 0

    if tree["type"] == "directory":
        dirs += 1
        for child in tree.get("children", []):
            child_files, child_dirs = _count_tree_items(child)
            files += child_files
            dirs += child_dirs
    else:
        files += 1

    return files, dirs


def _format_permissions_symbolic(mode: int) -> str:
    """Convert numeric mode to symbolic format (e.g., 'rw-r--r--').

    Args:
        mode: File mode from stat.st_mode

    Returns:
        str: Symbolic permission string (9 characters)
    """
    perms = []
    # Owner permissions
    perms.append("r" if mode & stat.S_IRUSR else "-")
    perms.append("w" if mode & stat.S_IWUSR else "-")
    perms.append("x" if mode & stat.S_IXUSR else "-")
    # Group permissions
    perms.append("r" if mode & stat.S_IRGRP else "-")
    perms.append("w" if mode & stat.S_IWGRP else "-")
    perms.append("x" if mode & stat.S_IXGRP else "-")
    # Others permissions
    perms.append("r" if mode & stat.S_IROTH else "-")
    perms.append("w" if mode & stat.S_IWOTH else "-")
    perms.append("x" if mode & stat.S_IXOTH else "-")
    return "".join(perms)


def validate_and_resolve_file(
    file_name: str, check_exists: bool = True
) -> Path:
    """Validate inputs and resolve file path in one step.

    Args:
        file_name: File name to validate and resolve
        check_exists: Whether to verify file exists

    Returns:
        Resolved Path object

    Raises:
        FileSecurityError: If validation fails
        FileOperationError: If file doesn't exist (when check_exists=True)
    """
    _validate_inputs(file_name)
    return _secure_resolve_path(file_name, check_exists=check_exists)


def validate_and_resolve_two_files(
    source: str, dest: str, dest_must_exist: bool = False
) -> tuple[Path, Path]:
    """Validate and resolve two file paths (for copy, rename operations).

    Args:
        source: Source file name
        dest: Destination file name
        dest_must_exist: Whether destination must exist

    Returns:
        Tuple of (source_path, dest_path)

    Raises:
        FileSecurityError: If validation fails
        FileOperationError: If files don't exist as required
    """
    _validate_inputs(source)
    _validate_inputs(dest)
    source_path = _secure_resolve_path(source)
    dest_path = _secure_resolve_path(dest, check_exists=dest_must_exist)
    return source_path, dest_path
