"""File write and modification operations."""

from pathlib import Path
from typing import List, Optional

from loguru import logger

from aria.tools.decorators import tool_function
from aria.tools.files._internals import (
    _create_backup,
    _secure_resolve_dir,
    _secure_resolve_path,
)
from aria.tools.files._responses import file_success_response
from aria.tools.files.decorators import (
    with_file_operation_error_handling,
    with_input_validation,
)
from aria.tools.files.exceptions import FileOperationError
from aria.tools.files.read_operations import _count_lines_efficiently


def _atomic_write(file_path: Path, content: str) -> None:
    """Write file atomically using temp file and rename.

    Args:
        file_path: Path to write to
        content: Content to write

    Raises:
        FileOperationError: If write fails
    """
    import tempfile

    tmp_path = None
    try:
        # Write to temp file in same directory (for atomic rename)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=file_path.parent,
            delete=False,
        ) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        # Atomic rename
        tmp_path.rename(file_path)
    except OSError as exc:
        # Clean up temp file if it exists
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()
        raise FileOperationError(f"Failed to write file: {exc}") from exc


def _modify_lines_streaming(
    file_path: Path, offset: int, length: int, new_lines: Optional[List[str]]
) -> tuple[int, int]:
    """Modify lines in file using streaming.

    Args:
        file_path: Path to the file
        offset: Starting line number (0-indexed)
        length: Number of lines to delete (0 = just insert)
        new_lines: Lines to insert (None = just delete)

    Returns:
        Tuple of (old_total_lines, new_total_lines)

    Raises:
        FileOperationError: If operation fails
    """
    import shutil

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
        if temp_path.exists():
            temp_path.unlink()
        raise FileOperationError(f"Failed to modify file: {exc}") from exc


@tool_function(
    "append_to_file",
    validate={"contents": True},
    error_handler=with_file_operation_error_handling,
    validation_decorator=with_input_validation,
)
def append_to_file(intent: str, file_name: str, contents: str) -> str:
    """
    Append text to an existing file.

    Args:
        intent: Why you're appending (e.g., "Adding log entry")
        file_name: Absolute path (e.g., /home/user/data/downloads/file.txt)
        contents: Text to append

    Returns:
        JSON with bytes_appended, new_total_lines, new_file_size
    """
    logger.info(f"Appending to file: {file_name}")

    # Resolve path
    resolved_path = _secure_resolve_path(file_name)

    # Append content
    with open(resolved_path, "a", encoding="utf-8") as f:
        f.write(contents)

    # Calculate metrics
    bytes_appended = len(contents.encode("utf-8"))
    new_total_lines = _count_lines_efficiently(resolved_path)
    new_file_size = resolved_path.stat().st_size

    # Build and return response
    data = {
        "file_name": file_name,
        "bytes_appended": bytes_appended,
        "new_total_lines": new_total_lines,
        "new_file_size": new_file_size,
    }
    logger.info(f"Successfully appended {bytes_appended} bytes to {file_name}")
    return file_success_response(intent, data)


@tool_function(
    "create_directory",
    validate={},
    error_handler=with_file_operation_error_handling,
    validation_decorator=with_input_validation,
)
def create_directory(intent: str, dir_name: str) -> str:
    """
    Create a directory (including parents).

    Args:
        intent: Why you're creating (e.g., "Setting up project structure")
        dir_name: Directory path relative to BASE_DIR

    Returns:
        JSON with dir_name, created, already_existed
    """
    logger.info(f"Creating directory: {dir_name}")

    # Resolve path (don't check exists since we're creating it)
    dir_path = _secure_resolve_dir(dir_name, check_exists=False)

    # Create directory
    already_existed = dir_path.exists()
    dir_path.mkdir(parents=True, exist_ok=True)

    # Build and return response
    data = {
        "dir_name": dir_name,
        "created": not already_existed,
        "already_existed": already_existed,
    }
    logger.info(f"Successfully created directory: {dir_name}")
    return file_success_response(intent, data)


@tool_function(
    "delete_lines_range",
    validate={"offset": True, "length": True},
    error_handler=with_file_operation_error_handling,
    validation_decorator=with_input_validation,
)
def delete_lines_range(
    intent: str, file_name: str, offset: int, length: int
) -> str:
    """
    Delete a contiguous range of lines from a file.

    Args:
        intent: Why you're deleting (e.g., "Removing obsolete code")
        file_name: Path relative to BASE_DIR
        offset: 0-indexed starting line
        length: Number of lines to delete

    Returns:
        JSON with lines_deleted, offset, old_total_lines,
        # new_total_lines, backup_created
    """
    logger.info(
        f"Deleting lines from {file_name} (offset={offset}, length={length})"
    )

    # Resolve path
    resolved_path = _secure_resolve_path(file_name)

    # Always create backup before deletion
    backup_path = _create_backup(resolved_path)

    # Delete lines using streaming
    old_total_lines, new_total_lines = _modify_lines_streaming(
        resolved_path, offset, length, None
    )

    # Build and return response
    data = {
        "file_name": file_name,
        "lines_deleted": length,
        "offset": offset,
        "old_total_lines": old_total_lines,
        "new_total_lines": new_total_lines,
        "backup_created": backup_path is not None,
    }
    logger.info(f"Successfully deleted {length} lines from {file_name}")
    return file_success_response(intent, data)


@tool_function(
    "insert_lines_at",
    validate={"offset": True, "new_lines": True},
    error_handler=with_file_operation_error_handling,
    validation_decorator=with_input_validation,
)
def insert_lines_at(
    intent: str, file_name: str, new_lines: List[str], offset: int
) -> str:
    """
    Insert lines at a given offset.

    Args:
        intent: Why you're inserting (e.g., "Adding new function")
        file_name: Path relative to BASE_DIR
        new_lines: List of lines to insert
        offset: 0-indexed line number to insert at

    Returns:
        JSON with lines_inserted, offset, old_total_lines, new_total_lines
    """
    logger.info(
        f"Inserting {len(new_lines)} lines at offset {offset} in {file_name}"
    )

    # Resolve path
    resolved_path = _secure_resolve_path(file_name)

    # Insert lines using streaming
    old_total_lines, new_total_lines = _modify_lines_streaming(
        resolved_path, offset, 0, new_lines
    )

    # Build and return response
    data = {
        "file_name": file_name,
        "lines_inserted": len(new_lines),
        "offset": offset,
        "old_total_lines": old_total_lines,
        "new_total_lines": new_total_lines,
    }
    logger.info(f"Successfully inserted {len(new_lines)} lines in {file_name}")
    return file_success_response(intent, data)


@tool_function(
    "replace_lines_range",
    validate={"offset": True, "length": True, "new_lines": True},
    error_handler=with_file_operation_error_handling,
    validation_decorator=with_input_validation,
)
def replace_lines_range(
    intent: str,
    file_name: str,
    new_lines: List[str],
    offset: int,
    length: int,
) -> str:
    """
    Replace a contiguous range of lines in a file.

    Args:
        intent: Why you're replacing (e.g., "Updating function")
        file_name: Path relative to BASE_DIR
        new_lines: Lines to insert
        offset: 0-indexed starting line
        length: Number of lines to replace

    Returns:
        JSON with lines_replaced, new_lines_inserted, backup_created
    """
    logger.info(f"Replacing {length} lines at offset {offset} in {file_name}")

    # Resolve path
    resolved_path = _secure_resolve_path(file_name)

    # Always create backup before modification
    backup_path = _create_backup(resolved_path)

    # Replace lines using streaming
    old_total_lines, new_total_lines = _modify_lines_streaming(
        resolved_path, offset, length, new_lines
    )

    # Build and return response
    data = {
        "file_name": file_name,
        "lines_replaced": length,
        "new_lines_inserted": len(new_lines),
        "offset": offset,
        "old_total_lines": old_total_lines,
        "new_total_lines": new_total_lines,
        "backup_created": backup_path is not None,
    }
    logger.info(f"Successfully replaced {length} lines in {file_name}")
    return file_success_response(intent, data)


@tool_function(
    "write_full_file",
    validate={"contents": True},
    error_handler=with_file_operation_error_handling,
    validation_decorator=with_input_validation,
)
def write_full_file(intent: str, file_name: str, contents: str) -> str:
    """
    Create/overwrite a file atomically.

    Args:
        intent: Why you're writing (e.g., "Creating new module")
        file_name: Absolute path (e.g., /home/user/data/downloads/file.txt)
        contents: Full file content

    Returns:
        JSON with bytes_written, lines_written, created, backup_created
    """
    logger.info(f"Writing full file: {file_name}")

    # Resolve path
    resolved_path = _secure_resolve_path(file_name, check_exists=False)

    # Check if file exists
    file_existed = resolved_path.exists()

    # Create backup if file exists
    backup_path = None
    if file_existed:
        backup_path = _create_backup(resolved_path)

    # Create parent directories
    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    # Write content atomically
    _atomic_write(resolved_path, contents)

    # Calculate metrics
    bytes_written = len(contents.encode("utf-8"))
    lines_written = contents.count("\n")
    if not contents.endswith("\n") and contents:
        lines_written += 1

    # Build and return response
    data = {
        "file_name": file_name,
        "bytes_written": bytes_written,
        "lines_written": lines_written,
        "created": not file_existed,
        "backup_created": backup_path is not None,
    }
    logger.info(f"Successfully wrote {bytes_written} bytes to {file_name}")
    return file_success_response(intent, data)
