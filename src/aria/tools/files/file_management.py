"""File management operations (copy, move, delete, rename)."""

from shutil import copy2
from typing import Optional

from loguru import logger

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
    intent: str,
    source: str,
    destination: str,
    overwrite: Optional[bool] = False,
) -> str:
    """
    Copy a file.

    Args:
        intent: Why you're copying (e.g., "Creating backup")
        source: Absolute path (e.g., /home/user/data/downloads/file.txt)
        destination: Absolute path (e.g., /home/user/data/downloads/file.txt)
        overwrite: If True, overwrite existing destination (default: False)

    Returns:
        JSON with source, destination, bytes_copied, success
    """
    logger.info(f"Copying file from {source} to {destination}")

    # Validate and resolve paths
    source_path, dest_path = validate_and_resolve_two_files(
        source, destination, dest_must_exist=False
    )

    # Check overwrite policy
    if dest_path.exists() and not overwrite:
        return file_error_response(
            intent,
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
    return file_success_response(intent, data, tool="copy_file")


@tool_function(
    "delete_file",
    error_handler=with_file_operation_error_handling,
)
def delete_file(intent: str, file_name: str) -> str:
    """
    Delete a file (creates a backup first).

    Args:
        intent: Why you're deleting (e.g., "Removing obsolete file")
        file_name: Path relative to BASE_DIR

    Returns:
        JSON with file_name, deleted, backup_created
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
    return file_success_response(intent, data, tool="delete_file")


@tool_function("move_file")
def move_file(intent: str, source: str, destination: str) -> str:
    """
    Move a file (alias for rename_file).

    Args:
        intent: Why you're moving (e.g., "Reorganizing project")
        source: Source path relative to BASE_DIR
        destination: Destination path relative to BASE_DIR

    Returns:
        JSON with source, destination, success
    """
    # Delegate to rename_file
    return rename_file(intent, source, destination)


@tool_function(
    "rename_file",
    error_handler=with_file_operation_error_handling,
)
def rename_file(intent: str, old_name: str, new_name: str) -> str:
    """
    Rename/move a file.

    Args:
        intent: Why you're renaming (e.g., "Fixing filename typo")
        old_name: Current path relative to BASE_DIR
        new_name: New path relative to BASE_DIR

    Returns:
        JSON with old_name, new_name, success
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
    return file_success_response(intent, data, tool="rename_file")
