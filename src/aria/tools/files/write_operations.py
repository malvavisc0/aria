"""File write and modification operations."""

from pathlib import Path

from loguru import logger

from aria.tools import Reason
from aria.tools.decorators import tool_function
from aria.tools.files._internals import _create_backup, _secure_resolve_path
from aria.tools.files._responses import file_success_response
from aria.tools.files.decorators import (
    with_file_operation_error_handling,
    with_input_validation,
)
from aria.tools.files.exceptions import FileOperationError
from aria.tools.files.unified_read import _count_lines_efficiently


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
    file_path: Path, offset: int, length: int, new_lines: list[str] | None
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
            open(file_path, encoding="utf-8") as infile,
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
    "write_file",
    validate={"contents": True},
    error_handler=with_file_operation_error_handling,
    validation_decorator=with_input_validation,
)
def write_file(
    reason: Reason,
    file_name: str,
    contents: str,
    mode: str = "overwrite",
) -> str:
    """Write or append to a file (atomic, dirs auto-created, backup on overwrite).

    Args:
        reason: Required. Brief explanation of why you are writing this file.
        file_name: File path.
        contents: Content to write.
        mode: overwrite|append (default: overwrite).

    Returns:
        JSON with bytes_written/appended, lines, created, backup_created.
    """
    if mode not in ("overwrite", "append"):
        raise FileOperationError(
            f"Invalid mode: {mode!r}. Must be 'overwrite' or 'append'."
        )

    if mode == "overwrite":
        return _write_file_overwrite(reason, file_name, contents)
    else:
        return _write_file_append(reason, file_name, contents)


def _write_file_overwrite(reason: str, file_name: str, contents: str) -> str:
    """Overwrite or create a file atomically."""
    logger.info(f"Writing file (overwrite): {file_name}")

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
        "mode": "overwrite",
        "bytes_written": bytes_written,
        "lines_written": lines_written,
        "created": not file_existed,
        "backup_created": backup_path is not None,
    }
    logger.info(f"Successfully wrote {bytes_written} bytes to {file_name}")
    return file_success_response(reason, data, tool="write_file")


def _write_file_append(reason: str, file_name: str, contents: str) -> str:
    """Append content to an existing file."""
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
        "mode": "append",
        "bytes_appended": bytes_appended,
        "new_total_lines": new_total_lines,
        "new_file_size": new_file_size,
    }
    logger.info(f"Successfully appended {bytes_appended} bytes to {file_name}")
    return file_success_response(reason, data, tool="write_file")


@tool_function(
    "edit_file",
    validate={"offset": True},
    error_handler=with_file_operation_error_handling,
    validation_decorator=with_input_validation,
)
def edit_file(
    reason: Reason,
    file_name: str,
    offset: int,
    length: int = 0,
    new_lines: list[str] | None = None,
) -> str:
    """Edit specific lines in a file (backup always created).

    Operation: length=0+new_lines→insert; length>0+new_lines→replace;
    length>0+new_lines=None→delete.

    Args:
        reason: Required. Brief explanation of why you are editing this file.
        file_name: File path.
        offset: 0-indexed start line.
        length: Lines to replace/delete (0=insert only).
        new_lines: Lines to insert/replace (None=delete).

    Returns:
        JSON with operation, offset, lines_affected, old/new total_lines.
    """
    # Determine operation type
    if length == 0 and new_lines is not None:
        operation = "insert"
    elif length > 0 and new_lines is not None:
        operation = "replace"
    elif length > 0 and new_lines is None:
        operation = "delete"
    else:
        raise FileOperationError(
            "Invalid edit_file parameters: provide new_lines for insert, "
            "or length>0 for replace/delete."
        )

    logger.info(
        f"Editing file {file_name}: {operation} (offset={offset}, length={length})"
    )

    # Resolve path
    resolved_path = _secure_resolve_path(file_name)

    # Always create backup before modification
    backup_path = _create_backup(resolved_path)

    # Modify lines using streaming
    old_total_lines, new_total_lines = _modify_lines_streaming(
        resolved_path, offset, length, new_lines
    )

    # Calculate lines affected
    if operation == "delete":
        lines_affected = length
    else:
        # insert or replace — new_lines is guaranteed non-None
        lines_affected = len(new_lines)  # type: ignore[arg-type]

    # Build and return response
    data = {
        "file_name": file_name,
        "operation": operation,
        "offset": offset,
        "length": length,
        "lines_affected": lines_affected,
        "old_total_lines": old_total_lines,
        "new_total_lines": new_total_lines,
        "backup_created": backup_path is not None,
    }
    logger.info(
        f"Successfully {operation}ed in {file_name}: "
        f"{old_total_lines} → {new_total_lines} lines"
    )
    return file_success_response(reason, data)
