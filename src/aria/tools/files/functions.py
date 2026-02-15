"""Secure file and directory operations."""

import inspect
import mimetypes
import os
import stat
from datetime import datetime
from shutil import copy2
from typing import List, Optional

from loguru import logger

from aria.tools.constants import BASE_DIR, MAX_FILE_SIZE
from aria.tools.files._internals import (
    _atomic_write,
    _build_directory_tree,
    _count_lines_efficiently,
    _count_tree_items,
    _create_backup,
    _error_response,
    _format_permissions_symbolic,
    _modify_lines_streaming,
    _read_lines_streaming,
    _safe_json,
    _secure_resolve_dir,
    _secure_resolve_path,
    _timestamp,
    validate_and_resolve_file,
    validate_and_resolve_two_files,
)
from aria.tools.files.decorators import (
    with_file_operation_error_handling,
    with_input_validation,
)
from aria.tools.files.exceptions import FileOperationError


@with_input_validation(contents=True)
@with_file_operation_error_handling("append_to_file")
def append_to_file(intent: str, file_name: str, contents: str) -> str:
    """
    Append text to an existing file.
    """
    logger.info(f"Appending to file: {file_name}")

    # Log reason
    frame = inspect.currentframe()
    if frame:
        func_name = frame.f_code.co_name
        logger.debug(f"Calling {func_name} to achieve: {intent}")

    # Resolve path (validation done by decorator)
    resolved_path = _secure_resolve_path(file_name)

    # Append content
    with open(resolved_path, "a", encoding="utf-8") as f:
        f.write(contents)

    # Calculate metrics
    bytes_appended = len(contents.encode("utf-8"))
    new_total_lines = _count_lines_efficiently(resolved_path)
    new_file_size = resolved_path.stat().st_size

    # Build and return response
    result = {
        "operation": "append_to_file",
        "result": {
            "file_name": file_name,
            "bytes_appended": bytes_appended,
            "new_total_lines": new_total_lines,
            "new_file_size": new_file_size,
        },
        "metadata": {"timestamp": _timestamp()},
    }
    logger.info(f"Successfully appended {bytes_appended} bytes to {file_name}")
    return _safe_json(result)


@with_file_operation_error_handling("copy_file")
def copy_file(
    intent: str,
    source: str,
    destination: str,
    overwrite: Optional[bool] = False,
) -> str:
    """
    Copy a file.
    """
    frame = inspect.currentframe()
    if frame:
        func_name = frame.f_code.co_name
        logger.debug(f"Calling {func_name} to achieve: {intent}")

    logger.info(f"Copying file from {source} to {destination}")

    # Validate and resolve paths
    source_path, dest_path = validate_and_resolve_two_files(
        source, destination, dest_must_exist=False
    )

    # Check overwrite policy
    if dest_path.exists() and not overwrite:
        return _error_response(
            "copy_file",
            destination,
            FileOperationError(
                f"Destination {destination} already exists and overwrite=False"
            ),
        )

    # Create parent directories and copy
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    copy2(source_path, dest_path)
    bytes_copied = dest_path.stat().st_size

    # Build and return response
    result = {
        "operation": "copy_file",
        "result": {
            "source": source,
            "destination": destination,
            "bytes_copied": bytes_copied,
            "success": True,
        },
        "metadata": {"timestamp": _timestamp()},
    }
    logger.info(f"Successfully copied {source} to {destination}")
    return _safe_json(result)


@with_input_validation()
@with_file_operation_error_handling("create_directory")
def create_directory(intent: str, dir_name: str) -> str:
    """
    Create a directory (including parents).
    """
    frame = inspect.currentframe()
    if frame:
        func_name = frame.f_code.co_name
        logger.debug(f"Calling {func_name} to achieve: {intent}")

    logger.info(f"Creating directory: {dir_name}")

    # Resolve path (validation done by decorator)
    dir_path = _secure_resolve_dir(dir_name)

    # Create directory
    already_existed = dir_path.exists()
    dir_path.mkdir(parents=True, exist_ok=True)

    # Build and return response
    result = {
        "operation": "create_directory",
        "result": {
            "dir_name": dir_name,
            "created": not already_existed,
            "already_existed": already_existed,
        },
        "metadata": {"timestamp": _timestamp()},
    }
    logger.info(f"Successfully created directory: {dir_name}")
    return _safe_json(result)


@with_file_operation_error_handling("delete_file")
def delete_file(intent: str, file_name: str) -> str:
    """
    Delete a file (creates a backup first).
    """
    frame = inspect.currentframe()
    if frame:
        func_name = frame.f_code.co_name
        logger.debug(f"Calling {func_name} to achieve: {intent}")

    logger.info(f"Deleting file: {file_name}")

    # Validate and resolve path
    resolved_path = validate_and_resolve_file(file_name)

    # Always create backup before deletion
    backup_path = _create_backup(resolved_path)

    # Delete file
    resolved_path.unlink()

    # Build and return response
    result = {
        "operation": "delete_file",
        "result": {
            "file_name": file_name,
            "deleted": True,
            "backup_created": backup_path is not None,
        },
        "metadata": {"timestamp": _timestamp()},
    }
    logger.info(f"Successfully deleted file: {file_name}")
    return _safe_json(result)


@with_input_validation(offset=True, length=True)
@with_file_operation_error_handling("delete_lines_range")
def delete_lines_range(intent: str, file_name: str, offset: int, length: int) -> str:
    """
    Delete a contiguous range of lines from a file.
    """
    frame = inspect.currentframe()
    if frame:
        func_name = frame.f_code.co_name
        logger.debug(f"Calling {func_name} to achieve: {intent}")

    logger.info(f"Deleting lines from {file_name} (offset={offset}, length={length})")

    # Resolve path (validation done by decorator)
    resolved_path = _secure_resolve_path(file_name)

    # Always create backup before deletion
    backup_path = _create_backup(resolved_path)

    # Delete lines using streaming
    old_total_lines, new_total_lines = _modify_lines_streaming(
        resolved_path, offset, length, None
    )

    # Build and return response
    result = {
        "operation": "delete_lines_range",
        "result": {
            "file_name": file_name,
            "lines_deleted": length,
            "offset": offset,
            "old_total_lines": old_total_lines,
            "new_total_lines": new_total_lines,
            "backup_created": backup_path is not None,
        },
        "metadata": {"timestamp": _timestamp()},
    }
    logger.info(f"Successfully deleted {length} lines from {file_name}")
    return _safe_json(result)


@with_file_operation_error_handling("file_exists")
def file_exists(intent: str, file_name: str) -> str:
    """
    Check whether a file/directory exists.
    """
    frame = inspect.currentframe()
    if frame:
        func_name = frame.f_code.co_name
        logger.debug(f"Calling {func_name} to achieve: {intent}")

    logger.info(f"Checking existence of: {file_name}")

    # Validate and resolve path (don't check existence yet)
    resolved_path = validate_and_resolve_file(file_name, check_exists=False)

    # Check existence and type
    exists = resolved_path.exists()
    is_file = resolved_path.is_file() if exists else False
    is_directory = resolved_path.is_dir() if exists else False

    # Build and return response
    result = {
        "operation": "file_exists",
        "result": {
            "file_name": file_name,
            "exists": exists,
            "is_file": is_file,
            "is_directory": is_directory,
        },
        "metadata": {"timestamp": _timestamp()},
    }
    logger.info(f"Existence check complete for: {file_name}")
    return _safe_json(result)


@with_input_validation()
@with_file_operation_error_handling("get_directory_tree")
def get_directory_tree(intent: str, path: str, max_depth: Optional[int] = 3) -> str:
    """
    Return a directory tree summary.
    """
    frame = inspect.currentframe()
    if frame:
        func_name = frame.f_code.co_name
        logger.debug(f"Calling {func_name} to achieve: {intent}")

    max_depth_value = 3 if max_depth is None else max_depth

    logger.info(f"Getting directory tree for: {path} (max_depth={max_depth_value})")

    # Resolve path (validation done by decorator)
    resolved_path = _secure_resolve_dir(path)

    if not resolved_path.exists():
        resolved_path = _secure_resolve_path(path, check_exists=False)

    # Build tree and count items
    tree = _build_directory_tree(resolved_path, 0, max_depth_value)
    total_files, total_directories = _count_tree_items(tree)

    # Build and return response
    result = {
        "operation": "get_directory_tree",
        "result": {
            "path": path,
            "tree": tree,
            "total_files": total_files,
            "total_directories": total_directories,
        },
        "metadata": {"timestamp": _timestamp()},
    }
    logger.info(f"Successfully built directory tree for: {path}")
    return _safe_json(result)


@with_file_operation_error_handling("get_file_info")
def get_file_info(intent: str, file_name: str) -> str:
    """
    Return file metadata (size/lines/type).
    """
    frame = inspect.currentframe()
    if frame:
        func_name = frame.f_code.co_name
        logger.debug(f"Calling {func_name} to achieve: {intent}")

    logger.info(f"Retrieving information for file: {file_name}")

    # Validate and resolve path
    resolved_path = validate_and_resolve_file(file_name)

    # Get file statistics
    file_stats = resolved_path.stat()
    line_count = _count_lines_efficiently(resolved_path)

    # Check file size limit
    if file_stats.st_size > MAX_FILE_SIZE:
        return _error_response(
            "get_file_info",
            file_name,
            FileOperationError("File size exceeds maximum allowed limit"),
        )

    # Build and return response
    result = {
        "operation": "get_file_info",
        "result": {
            "file_name": file_name,
            "total_lines": line_count,
            "file_size_bytes": file_stats.st_size,
            "mime_type": mimetypes.guess_type(file_name)[0],
        },
        "metadata": {"timestamp": _timestamp()},
    }

    logger.info(f"Successfully retrieved information for file: {file_name}")
    return _safe_json(result)


@with_file_operation_error_handling("get_file_permissions")
def get_file_permissions(intent: str, file_name: str) -> str:
    """
    Return file permissions/ownership info.
    """
    frame = inspect.currentframe()
    if frame:
        func_name = frame.f_code.co_name
        logger.debug(f"Calling {func_name} to achieve: {intent}")

    logger.info(f"Retrieving permissions for file: {file_name}")

    # Validate and resolve path
    resolved_path = validate_and_resolve_file(file_name)

    # Get file statistics
    file_stats = resolved_path.stat()
    file_mode = file_stats.st_mode

    # Extract permission bits (last 9 bits)
    mode_octal = oct(stat.S_IMODE(file_mode))
    mode_symbolic = _format_permissions_symbolic(file_mode)

    # Break down permissions by category
    permissions = {
        "owner": {
            "read": bool(file_mode & stat.S_IRUSR),
            "write": bool(file_mode & stat.S_IWUSR),
            "execute": bool(file_mode & stat.S_IXUSR),
        },
        "group": {
            "read": bool(file_mode & stat.S_IRGRP),
            "write": bool(file_mode & stat.S_IWGRP),
            "execute": bool(file_mode & stat.S_IXGRP),
        },
        "others": {
            "read": bool(file_mode & stat.S_IROTH),
            "write": bool(file_mode & stat.S_IWOTH),
            "execute": bool(file_mode & stat.S_IXOTH),
        },
    }

    # Check actual accessibility (considers current user/process)
    is_readable = os.access(resolved_path, os.R_OK)
    is_writable = os.access(resolved_path, os.W_OK)
    is_executable = os.access(resolved_path, os.X_OK)

    # Get timestamps
    last_modified = datetime.fromtimestamp(file_stats.st_mtime).isoformat()
    last_accessed = datetime.fromtimestamp(file_stats.st_atime).isoformat()

    # Build and return response
    result = {
        "operation": "get_file_permissions",
        "result": {
            "file_name": file_name,
            "mode_octal": mode_octal,
            "mode_symbolic": mode_symbolic,
            "permissions": permissions,
            "is_readable": is_readable,
            "is_writable": is_writable,
            "is_executable": is_executable,
            "owner_uid": file_stats.st_uid,
            "group_gid": file_stats.st_gid,
            "last_modified": last_modified,
            "last_accessed": last_accessed,
        },
        "metadata": {"timestamp": _timestamp()},
    }

    logger.info(f"Successfully retrieved permissions for: {file_name}")
    return _safe_json(result)


@with_input_validation(offset=True, new_lines=True)
@with_file_operation_error_handling("insert_lines_at")
def insert_lines_at(
    intent: str, file_name: str, new_lines: List[str], offset: int
) -> str:
    """
    Insert lines at a given offset.
    """
    frame = inspect.currentframe()
    if frame:
        func_name = frame.f_code.co_name
        logger.debug(f"Calling {func_name} to achieve: {intent}")

    logger.info(f"Inserting {len(new_lines)} lines at offset {offset} in {file_name}")

    # Resolve path (validation done by decorator)
    resolved_path = _secure_resolve_path(file_name)

    # Insert lines using streaming
    old_total_lines, new_total_lines = _modify_lines_streaming(
        resolved_path, offset, 0, new_lines
    )

    # Build and return response
    result = {
        "operation": "insert_lines_at",
        "result": {
            "file_name": file_name,
            "lines_inserted": len(new_lines),
            "offset": offset,
            "old_total_lines": old_total_lines,
            "new_total_lines": new_total_lines,
        },
        "metadata": {"timestamp": _timestamp()},
    }
    logger.info(f"Successfully inserted {len(new_lines)} lines in {file_name}")
    return _safe_json(result)


@with_file_operation_error_handling("list_files")
def list_files(
    intent: str,
    pattern: Optional[str] = "**/*",
    recursive: Optional[bool] = False,
    max_results: Optional[int] = 100,
) -> str:
    """
    List files matching a glob pattern.
    """
    frame = inspect.currentframe()
    if frame:
        func_name = frame.f_code.co_name
        logger.debug(f"Calling {func_name} to achieve: {intent}")

    pattern_value = pattern or "**/*"
    recursive_value = False if recursive is None else recursive
    max_results_value = 100 if max_results is None else max_results

    logger.info(
        "Listing files with pattern: %s (recursive=%s)"
        % (pattern_value, recursive_value)
    )

    # Get matches based on recursive flag
    if recursive_value:
        matches = list(BASE_DIR.rglob(pattern_value))
    else:
        matches = list(BASE_DIR.glob(pattern_value))

    # Filter to only files and convert to relative paths
    files = []
    for match in matches:
        if match.is_file():
            try:
                rel_path = match.relative_to(BASE_DIR)
                files.append(str(rel_path))
                if len(files) >= max_results_value:
                    break
            except ValueError:
                continue

    truncated = len(matches) > max_results_value

    # Build and return response
    result = {
        "operation": "list_files",
        "result": {
            "pattern": pattern_value,
            "files": files,
            "count": len(files),
            "truncated": truncated,
        },
        "metadata": {"timestamp": _timestamp()},
    }
    logger.info(f"Found {len(files)} files matching pattern {pattern_value}")
    return _safe_json(result)


def move_file(intent: str, source: str, destination: str) -> str:
    """
    Move a file (alias for rename_file).
    """
    frame = inspect.currentframe()
    if frame:
        func_name = frame.f_code.co_name
        logger.debug(f"Calling {func_name} to achieve: {intent}")

    return rename_file(intent, source, destination)


@with_input_validation(chunk_size=True, offset=True)
@with_file_operation_error_handling("read_file_chunk")
def read_file_chunk(
    intent: str,
    file_name: str,
    chunk_size: Optional[int] = 100,
    offset: Optional[int] = 0,
) -> str:
    """
    Read a file in chunks (preferred read method).
    """
    frame = inspect.currentframe()
    if frame:
        func_name = frame.f_code.co_name
        logger.debug(f"Calling {func_name} to achieve: {intent}")

    chunk_size_value = 100 if chunk_size is None else chunk_size
    offset_value = 0 if offset is None else offset

    logger.info(
        "Reading chunk from %s (offset=%s, size=%s)"
        % (file_name, offset_value, chunk_size_value)
    )

    # Resolve path (validation done by decorator)
    resolved_path = _secure_resolve_path(file_name)

    # Read chunk and calculate pagination
    total_lines = _count_lines_efficiently(resolved_path)
    lines = _read_lines_streaming(
        resolved_path,
        offset_value,
        chunk_size_value,
    )
    lines_returned = len(lines)
    next_offset = offset_value + lines_returned
    has_more = next_offset < total_lines

    # Build and return response
    result = {
        "operation": "read_file_chunk",
        "result": {
            "file_name": file_name,
            "lines": lines,
            "offset": offset_value,
            "chunk_size": chunk_size_value,
            "lines_returned": lines_returned,
            "total_lines": total_lines,
            "has_more": has_more,
            "next_offset": next_offset if has_more else None,
        },
        "metadata": {"timestamp": _timestamp()},
    }
    logger.info(f"Successfully read {lines_returned} lines from {file_name}")
    return _safe_json(result)


@with_file_operation_error_handling("read_full_file")
def read_full_file(intent: str, file_name: str, max_lines: Optional[int] = 500) -> str:
    """
    Read an entire small file.
    """
    frame = inspect.currentframe()
    if frame:
        func_name = frame.f_code.co_name
        logger.debug(f"Calling {func_name} to achieve: {intent}")

    logger.info(f"Reading full file: {file_name}")

    # Validate and resolve path
    resolved_path = validate_and_resolve_file(file_name)

    max_lines_value = 500 if max_lines is None else max_lines

    # Check file size limit
    total_lines = _count_lines_efficiently(resolved_path)
    if total_lines > max_lines_value:
        msg = (
            "File has %s lines, exceeds limit of %s. "
            "Use read_file_chunk() instead." % (total_lines, max_lines_value)
        )
        return _error_response(
            "read_full_file",
            file_name,
            FileOperationError(msg),
        )

    # Read full content
    with open(resolved_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Build and return response
    result = {
        "operation": "read_full_file",
        "result": {
            "file_name": file_name,
            "content": content,
            "total_lines": total_lines,
        },
        "metadata": {"timestamp": _timestamp()},
    }
    logger.info(f"Successfully read full file: {file_name}")
    return _safe_json(result)


@with_file_operation_error_handling("rename_file")
def rename_file(intent: str, old_name: str, new_name: str) -> str:
    """
    Rename/move a file.
    """
    frame = inspect.currentframe()
    if frame:
        func_name = frame.f_code.co_name
        logger.debug(f"Calling {func_name} to achieve: {intent}")

    logger.info(f"Renaming file from {old_name} to {new_name}")

    # Validate and resolve paths
    old_path, new_path = validate_and_resolve_two_files(
        old_name, new_name, dest_must_exist=False
    )

    # Create parent directories and rename
    new_path.parent.mkdir(parents=True, exist_ok=True)
    old_path.rename(new_path)

    # Build and return response
    result = {
        "operation": "rename_file",
        "result": {
            "old_name": old_name,
            "new_name": new_name,
            "success": True,
        },
        "metadata": {"timestamp": _timestamp()},
    }
    logger.info(f"Successfully renamed {old_name} to {new_name}")
    return _safe_json(result)


@with_input_validation(offset=True, length=True, new_lines=True)
@with_file_operation_error_handling("replace_lines_range")
def replace_lines_range(
    intent: str,
    file_name: str,
    new_lines: List[str],
    offset: int,
    length: int,
) -> str:
    """
    Replace a contiguous range of lines in a file.
    """
    frame = inspect.currentframe()
    if frame:
        func_name = frame.f_code.co_name
        logger.debug(f"Calling {func_name} to achieve: {intent}")

    logger.info(f"Replacing {length} lines at offset {offset} in {file_name}")

    # Resolve path (validation done by decorator)
    resolved_path = _secure_resolve_path(file_name)

    # Always create backup before modification
    backup_path = _create_backup(resolved_path)

    # Replace lines using streaming
    old_total_lines, new_total_lines = _modify_lines_streaming(
        resolved_path, offset, length, new_lines
    )

    # Build and return response
    result = {
        "operation": "replace_lines_range",
        "result": {
            "file_name": file_name,
            "lines_replaced": length,
            "new_lines_inserted": len(new_lines),
            "offset": offset,
            "old_total_lines": old_total_lines,
            "new_total_lines": new_total_lines,
            "backup_created": backup_path is not None,
        },
        "metadata": {"timestamp": _timestamp()},
    }
    logger.info(f"Successfully replaced {length} lines in {file_name}")
    return _safe_json(result)


@with_file_operation_error_handling("search_files_by_name")
def search_files_by_name(
    intent: str,
    regex_pattern: str,
    recursive: Optional[bool] = True,
    max_results: Optional[int] = 500,
) -> str:
    """
    Search for files by name using a regex.
    """
    frame = inspect.currentframe()
    if frame:
        func_name = frame.f_code.co_name
        logger.debug(f"Calling {func_name} to achieve: {intent}")

    logger.info(f"Searching files by name with pattern: {regex_pattern}")

    import re

    # Compile regex pattern
    try:
        pattern = re.compile(regex_pattern)
    except re.error as exc:
        logger.error(f"Invalid regex pattern {regex_pattern}: {exc}")
        return _error_response(
            "search_files_by_name",
            regex_pattern,
            FileOperationError(f"Invalid regex pattern: {exc}"),
        )

    recursive_value = True if recursive is None else recursive
    max_results_value = 500 if max_results is None else max_results

    # Search for matching files
    matches = []
    paths = BASE_DIR.rglob("*") if recursive_value else BASE_DIR.glob("*")

    for path in paths:
        if path.is_file() and pattern.search(path.name):
            try:
                rel_path = path.relative_to(BASE_DIR)
                matches.append(str(rel_path))
                if len(matches) >= max_results_value:
                    break
            except ValueError:
                continue

    truncated = len(matches) >= max_results_value

    # Build and return response
    result = {
        "operation": "search_files_by_name",
        "result": {
            "pattern": regex_pattern,
            "matches": matches,
            "count": len(matches),
            "truncated": truncated,
        },
        "metadata": {"timestamp": _timestamp()},
    }
    logger.info(f"Found {len(matches)} files matching pattern {regex_pattern}")
    return _safe_json(result)


@with_file_operation_error_handling("search_in_files")
def search_in_files(
    intent: str,
    regex_pattern: str,
    file_pattern: str = "**/*",
    recursive: bool = False,
    max_files: int = 100,
    max_matches: int = 500,
    context_lines: int = 2,
) -> str:
    """
    Search file contents using a regex.
    """
    frame = inspect.currentframe()
    if frame:
        func_name = frame.f_code.co_name
        logger.debug(f"Calling {func_name} to achieve: {intent}")

    logger.info(f"Searching in files with pattern: {regex_pattern}")

    import re

    # Compile regex pattern
    try:
        pattern = re.compile(regex_pattern)
    except re.error as exc:
        logger.error(f"Invalid regex pattern {regex_pattern}: {exc}")
        return _error_response(
            "search_in_files",
            regex_pattern,
            FileOperationError(f"Invalid regex pattern: {exc}"),
        )

    # Get file paths to search
    matches = []
    files_searched = 0
    paths = list(
        BASE_DIR.rglob(file_pattern) if recursive else BASE_DIR.glob(file_pattern)
    )

    # Search through files
    for path in paths:
        if not path.is_file() or files_searched >= max_files:
            if files_searched >= max_files:
                break
            continue

        files_searched += 1

        try:
            rel_path = str(path.relative_to(BASE_DIR))

            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines):
                if len(matches) >= max_matches:
                    break

                if pattern.search(line):
                    # Get context before and after
                    start = max(0, line_num - context_lines)
                    end = min(len(lines), line_num + context_lines + 1)

                    context_before = [
                        lines[i].rstrip("\n\r") for i in range(start, line_num)
                    ]
                    context_after = [
                        lines[i].rstrip("\n\r") for i in range(line_num + 1, end)
                    ]

                    matches.append(
                        {
                            "file": rel_path,
                            "line_number": line_num + 1,
                            "line_content": line.rstrip("\n\r"),
                            "context_before": context_before,
                            "context_after": context_after,
                        }
                    )

            if len(matches) >= max_matches:
                break

        except (OSError, UnicodeDecodeError):
            continue

    truncated = len(matches) >= max_matches or files_searched >= max_files

    # Build and return response
    result = {
        "operation": "search_in_files",
        "result": {
            "pattern": regex_pattern,
            "matches": matches,
            "total_matches": len(matches),
            "files_searched": files_searched,
            "truncated": truncated,
        },
        "metadata": {"timestamp": _timestamp()},
    }
    logger.info(f"Found {len(matches)} matches in {files_searched} files")
    return _safe_json(result)


@with_input_validation(contents=True)
@with_file_operation_error_handling("write_full_file")
def write_full_file(intent: str, file_name: str, contents: str) -> str:
    """
    Create/overwrite a file atomically.
    """
    frame = inspect.currentframe()
    if frame:
        func_name = frame.f_code.co_name
        logger.debug(f"Calling {func_name} to achieve: {intent}")

    logger.info(f"Writing full file: {file_name}")

    # Resolve path (validation done by decorator)
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
    result = {
        "operation": "write_full_file",
        "result": {
            "file_name": file_name,
            "bytes_written": bytes_written,
            "lines_written": lines_written,
            "created": not file_existed,
            "backup_created": backup_path is not None,
        },
        "metadata": {"timestamp": _timestamp()},
    }
    logger.info(f"Successfully wrote {bytes_written} bytes to {file_name}")
    return _safe_json(result)
