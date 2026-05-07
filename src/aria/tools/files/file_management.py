"""File management operations (copy, move, delete, rename)."""

from shutil import copy2

from loguru import logger

from aria.tools import Reason
from aria.tools.decorators import tool_function
from aria.tools.files._internals import (
    _create_backup,
    validate_and_resolve_file,
    validate_and_resolve_two_files,
)
from aria.tools.files._responses import (
    file_error_response,
    file_success_response,
)
from aria.tools.files.decorators import with_file_operation_error_handling
from aria.tools.files.exceptions import FileOperationError


@tool_function(
    "copy_file",
    error_handler=with_file_operation_error_handling,
)
def copy_file(
    reason: Reason,
    source: str,
    destination: str,
    overwrite: bool | None = False,
) -> str:
    """Copy a file to a new location (dirs auto-created).

    Args:
        reason: Required. Brief explanation of why you are copying this file.
        source: Source file path.
        destination: Destination path.
        overwrite: Overwrite if exists (default: False).

    Returns:
        JSON with source, destination, bytes_copied, success.
    """
    logger.info(f"Copying file from {source} to {destination}")

    # Validate and resolve paths
    source_path, dest_path = validate_and_resolve_two_files(
        source, destination, dest_must_exist=False
    )

    # Check overwrite policy
    if dest_path.exists() and not overwrite:
        return file_error_response(
            reason,
            FileOperationError(
                f"Destination {destination} already exists and overwrite=False"
            ),
        )

    # Create parent directories and copy
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    copy2(source_path, dest_path)
    bytes_copied = dest_path.stat().st_size

    # Build and return response
    data = {
        "source": source,
        "destination": destination,
        "bytes_copied": bytes_copied,
        "success": True,
    }
    logger.info(f"Successfully copied {source} to {destination}")
    return file_success_response(reason, data, tool="copy_file")


@tool_function(
    "delete_file",
    error_handler=with_file_operation_error_handling,
)
def delete_file(reason: Reason, file_name: str) -> str:
    """
    Delete a file with automatic backup.

    When to use:
        - Use this to remove files that are no longer needed.
        - Do NOT use this to rename or move files — use `rename_file`.

    Why:
        A backup is always created before deletion, so you can recover
        the file if the deletion was a mistake.

    Args:
        reason: Required. Brief explanation of why you are deleting this file.
        file_name: Path relative to BASE_DIR.

    Returns:
        JSON with file_name, deleted, backup_created.

    Important:
        - A backup is always created before deletion.
        - Only files can be deleted (not directories).
    """
    logger.info(f"Deleting file: {file_name}")

    # Validate and resolve path
    resolved_path = validate_and_resolve_file(file_name)

    # Always create backup before deletion
    backup_path = _create_backup(resolved_path)

    # Delete file
    resolved_path.unlink()

    # Build and return response
    data = {
        "file_name": file_name,
        "deleted": True,
        "backup_created": backup_path is not None,
    }
    logger.info(f"Successfully deleted file: {file_name}")
    return file_success_response(reason, data, tool="delete_file")


@tool_function(
    "rename_file",
    error_handler=with_file_operation_error_handling,
)
def rename_file(reason: Reason, old_name: str, new_name: str) -> str:
    """
    Rename or move a file to a new location.

    When to use:
        - Use this to rename a file (fix a typo, change extension).
        - Use this to move a file to a different directory.
        - Do NOT use this to copy files — use `copy_file`.
        - Do NOT use this to delete files — use `delete_file`.

    Why:
        Renaming/moving is atomic on most filesystems and is the
        standard way to reorganize files without duplicating data.

    Args:
        reason: Required. Brief explanation of why you are renaming this file.
        old_name: Current path relative to BASE_DIR.
        new_name: New path relative to BASE_DIR.

    Returns:
        JSON with old_name, new_name, success.

    Important:
        - Destination parent directories are created automatically.
        - This is a move operation — the source file will no longer exist
          at old_name after success.
    """
    logger.info(f"Renaming file from {old_name} to {new_name}")

    # Validate and resolve paths
    old_path, new_path = validate_and_resolve_two_files(
        old_name, new_name, dest_must_exist=False
    )

    # Create parent directories and rename
    new_path.parent.mkdir(parents=True, exist_ok=True)
    old_path.rename(new_path)

    # Build and return response
    data = {
        "old_name": old_name,
        "new_name": new_name,
        "success": True,
    }
    logger.info(f"Successfully renamed {old_name} to {new_name}")
    return file_success_response(reason, data, tool="rename_file")
