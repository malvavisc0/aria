"""Read-only file operations."""

import mimetypes
import os
import re
import stat
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from aria.tools.constants import BASE_DIR, MAX_FILE_SIZE
from aria.tools.decorators import tool_function
from aria.tools.files._internals import (
    _secure_resolve_dir,
    _secure_resolve_path,
    validate_and_resolve_file,
)
from aria.tools.files._responses import (
    file_error_response,
    file_success_response,
)
from aria.tools.files.decorators import (
    with_file_operation_error_handling,
    with_input_validation,
)
from aria.tools.files.exceptions import FileOperationError


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


def _build_directory_tree(
    path: Path, current_depth: int, max_depth: int
) -> Dict[str, Any]:
    """Build directory tree structure recursively.

    Args:
        path: Path to build tree from
        current_depth: Current recursion depth
        max_depth: Maximum depth to recurse

    Returns:
        Dict representing directory tree
    """
    if current_depth >= max_depth:
        return {"type": "truncated"}

    try:
        entries = sorted(
            path.iterdir(), key=lambda p: (not p.is_dir(), p.name)
        )
    except PermissionError:
        return {"type": "permission_denied"}

    tree = {"type": "directory", "children": {}}

    for entry in entries:
        name = entry.name
        if entry.is_dir():
            if current_depth + 1 < max_depth:
                tree["children"][name] = _build_directory_tree(
                    entry, current_depth + 1, max_depth
                )
            else:
                tree["children"][name] = {"type": "directory", "children": {}}
        else:
            tree["children"][name] = {
                "type": "file",
                "size": entry.stat().st_size,
            }

    return tree


def _count_tree_items(tree: Dict[str, Any]) -> tuple[int, int]:
    """Count total files and directories in tree.

    Args:
        tree: Directory tree structure

    Returns:
        Tuple of (total_files, total_directories)
    """
    if (
        tree.get("type") == "truncated"
        or tree.get("type") == "permission_denied"
    ):
        return 0, 0

    files = 0
    dirs = 0

    children = tree.get("children", {})
    for item in children.values():
        if item.get("type") == "file":
            files += 1
        elif item.get("type") == "directory":
            dirs += 1
            sub_files, sub_dirs = _count_tree_items(item)
            files += sub_files
            dirs += sub_dirs

    return files, dirs


def _format_permissions_symbolic(mode: int) -> str:
    """Convert numeric mode to symbolic format (e.g., 'rw-r--r--').

    Args:
        mode: Numeric file mode

    Returns:
        Symbolic permission string
    """
    perms = []
    for who in "USR", "GRP", "OTH":
        for what in "R", "W", "X":
            bit = getattr(stat, f"S_I{what}{who}")
            perms.append(what.lower() if mode & bit else "-")
    return "".join(perms)


@tool_function(
    "file_exists",
    error_handler=with_file_operation_error_handling,
)
def file_exists(intent: str, file_name: str) -> str:
    """
    Check whether a file/directory exists.

    Args:
        intent: Why you're checking (e.g., "Verifying config exists")
        file_name: Path relative to BASE_DIR

    Returns:
        JSON with exists, is_file, is_directory
    """
    logger.info(f"Checking existence of: {file_name}")

    # Validate and resolve path (don't check existence yet)
    resolved_path = validate_and_resolve_file(file_name, check_exists=False)

    # Check existence and type
    exists = resolved_path.exists()
    is_file = resolved_path.is_file() if exists else False
    is_directory = resolved_path.is_dir() if exists else False

    # Build and return response
    data = {
        "file_name": file_name,
        "exists": exists,
        "is_file": is_file,
        "is_directory": is_directory,
    }
    logger.info(f"Existence check complete for: {file_name}")
    return file_success_response(intent, data)


@tool_function(
    "get_directory_tree",
    validate={},
    error_handler=with_file_operation_error_handling,
    validation_decorator=with_input_validation,
)
def get_directory_tree(
    intent: str, path: str, max_depth: Optional[int] = 3
) -> str:
    """
    Return a directory tree summary.

    Args:
        intent: Why you're getting tree (e.g., "Exploring project structure")
        path: Directory path relative to BASE_DIR
        max_depth: Maximum depth to traverse (default: 3)

    Returns:
        JSON with tree structure, total_files, total_directories
    """
    max_depth_value = 3 if max_depth is None else max_depth

    logger.info(
        f"Getting directory tree for: {path} (max_depth={max_depth_value})"
    )

    # Resolve path
    resolved_path = _secure_resolve_dir(path)

    if not resolved_path.exists():
        resolved_path = _secure_resolve_path(path, check_exists=False)

    # Build tree and count items
    tree = _build_directory_tree(resolved_path, 0, max_depth_value)
    total_files, total_directories = _count_tree_items(tree)

    # Build and return response
    data = {
        "path": path,
        "tree": tree,
        "total_files": total_files,
        "total_directories": total_directories,
    }
    logger.info(f"Successfully built directory tree for: {path}")
    return file_success_response(intent, data)


@tool_function(
    "get_file_info",
    error_handler=with_file_operation_error_handling,
)
def get_file_info(intent: str, file_name: str) -> str:
    """
    Return file metadata (size/lines/type/timestamps).

    Args:
        intent: Why you're checking (e.g., "Determining read strategy")
        file_name: Path relative to BASE_DIR

    Returns:
        JSON with file_name, size_bytes, size_mb, total_lines, mime_type,
        modified, created, is_directory, is_file, is_symlink
    """
    logger.info(f"Retrieving information for file: {file_name}")

    # Validate and resolve path
    resolved_path = validate_and_resolve_file(file_name)

    # Get file statistics
    file_stats = resolved_path.stat()
    line_count = _count_lines_efficiently(resolved_path)

    # Check file size limit
    if file_stats.st_size > MAX_FILE_SIZE:
        return file_error_response(
            intent,
            FileOperationError("File size exceeds maximum allowed limit"),
        )

    # Build and return response
    data = {
        "file_name": file_name,
        "size_bytes": file_stats.st_size,
        "size_mb": round(file_stats.st_size / (1024 * 1024), 4),
        "total_lines": line_count,
        "mime_type": mimetypes.guess_type(file_name)[0],
        "modified": datetime.fromtimestamp(file_stats.st_mtime).strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "created": datetime.fromtimestamp(file_stats.st_ctime).strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "is_directory": stat.S_ISDIR(file_stats.st_mode),
        "is_file": stat.S_ISREG(file_stats.st_mode),
        "is_symlink": stat.S_ISLNK(file_stats.st_mode),
    }

    logger.info(f"Successfully retrieved information for file: {file_name}")
    return file_success_response(intent, data)


@tool_function(
    "get_file_permissions",
    error_handler=with_file_operation_error_handling,
)
def get_file_permissions(intent: str, file_name: str) -> str:
    """
    Return file permissions/ownership info.

    Args:
        intent: Why you're checking (e.g., "Debugging access issue")
        file_name: Path relative to BASE_DIR

    Returns:
        JSON with mode_octal, mode_symbolic, permissions, is_readable,
        is_writable
    """
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
    data = {
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
    }
    logger.info(f"Successfully retrieved permissions for file: {file_name}")
    return file_success_response(intent, data)


@tool_function(
    "list_files",
    error_handler=with_file_operation_error_handling,
)
def list_files(
    intent: str,
    pattern: Optional[str] = "*",
    recursive: Optional[bool] = False,
    max_results: Optional[int] = 100,
) -> str:
    """
    List files matching a glob pattern.

    Args:
        intent: Why you're listing (e.g., "Finding all Python files")
        pattern: Glob pattern relative to BASE_DIR (default: "*")
        recursive: Search recursively from BASE_DIR (default: False)
        max_results: Maximum results (default: 100)

    Returns:
        JSON with files, count, truncated
    """
    pattern_value = pattern or "*"
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
    data = {
        "pattern": pattern_value,
        "files": files,
        "count": len(files),
        "truncated": truncated,
    }
    logger.info(f"Found {len(files)} files matching pattern {pattern_value}")
    return file_success_response(intent, data)


@tool_function(
    "read_file_chunk",
    validate={"chunk_size": True, "offset": True},
    error_handler=with_file_operation_error_handling,
    validation_decorator=with_input_validation,
)
def read_file_chunk(
    intent: str,
    file_name: str,
    chunk_size: Optional[int] = 100,
    offset: Optional[int] = 0,
) -> str:
    """
    Read a file in chunks (preferred read method).

    Args:
        intent: Why you're reading (e.g., "Inspecting config file")
        file_name: Absolute path (e.g., /home/user/data/downloads/file.txt)
        chunk_size: Lines to read (default: 100)
        offset: 0-indexed starting line (default: 0)

    Returns:
        JSON with lines, offset, total_lines, has_more, next_offset
    """
    chunk_size_value = 100 if chunk_size is None else chunk_size
    offset_value = 0 if offset is None else offset

    logger.info(
        "Reading chunk from %s (offset=%s, size=%s)"
        % (file_name, offset_value, chunk_size_value)
    )

    # Resolve path
    resolved_path = _secure_resolve_path(file_name)

    # Read chunk and calculate pagination
    total_lines = _count_lines_efficiently(resolved_path)
    lines = _read_lines_streaming(
        resolved_path, offset_value, chunk_size_value
    )
    lines_returned = len(lines)
    next_offset = offset_value + lines_returned
    has_more = next_offset < total_lines

    # Build and return response
    data = {
        "file_name": file_name,
        "lines": lines,
        "offset": offset_value,
        "chunk_size": chunk_size_value,
        "lines_returned": lines_returned,
        "total_lines": total_lines,
        "has_more": has_more,
        "next_offset": next_offset if has_more else None,
    }
    logger.info(f"Successfully read {lines_returned} lines from {file_name}")
    return file_success_response(intent, data)


@tool_function(
    "read_full_file",
    error_handler=with_file_operation_error_handling,
)
def read_full_file(
    intent: str, file_name: str, max_lines: Optional[int] = 500
) -> str:
    """
    Read an entire small file.

    Args:
        intent: Why you're reading (e.g., "Loading config")
        file_name: Absolute path (e.g., /home/user/data/downloads/file.txt)
        max_lines: Maximum lines allowed (default: 500)

    Returns:
        JSON with content, total_lines. Use read_file_chunk for large files.
    """
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
        return file_error_response(
            intent,
            FileOperationError(msg),
        )

    # Read full content
    with open(resolved_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Build and return response
    data = {
        "file_name": file_name,
        "content": content,
        "total_lines": total_lines,
        "max_lines_used": max_lines_value,
    }
    logger.info(f"Successfully read {total_lines} lines from {file_name}")
    return file_success_response(intent, data)


@tool_function(
    "search_files_by_name",
    error_handler=with_file_operation_error_handling,
)
def search_files_by_name(
    intent: str,
    regex_pattern: str,
    recursive: Optional[bool] = True,
    max_results: Optional[int] = 500,
) -> str:
    """
    Search for files by name using a regex pattern from BASE_DIR.

    Args:
        intent: Why you're searching (e.g., "Finding test files")
        regex_pattern: Regex to match against filenames
        recursive: Search recursively (default: True)
        max_results: Maximum results (default: 500)

    Returns:
        JSON with matches, count, truncated
    """
    logger.info(f"Searching files by name with pattern: {regex_pattern}")

    # Compile regex pattern
    try:
        pattern = re.compile(regex_pattern)
    except re.error as exc:
        logger.error(f"Invalid regex pattern {regex_pattern}: {exc}")
        return file_error_response(
            intent,
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
    data = {
        "pattern": regex_pattern,
        "matches": matches,
        "count": len(matches),
        "truncated": truncated,
    }
    logger.info(f"Found {len(matches)} files matching pattern {regex_pattern}")
    return file_success_response(intent, data)


@tool_function(
    "search_in_files",
    error_handler=with_file_operation_error_handling,
)
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
    Search file contents using a regex within files matched from BASE_DIR.

    Args:
        intent: Why you're searching (e.g., "Finding TODOs")
        regex_pattern: Regex to match in file contents
        file_pattern: Glob pattern for files (default: "**/*")
        recursive: Search recursively (default: False)
        max_files: Max files to search (default: 100)
        max_matches: Max matches (default: 500)
        context_lines: Context lines around match (default: 2)

    Returns:
        JSON with matches (file, line_number, line_content, context)
    """
    logger.info(f"Searching in files with pattern: {regex_pattern}")

    # Compile regex pattern
    try:
        pattern = re.compile(regex_pattern)
    except re.error as exc:
        logger.error(f"Invalid regex pattern {regex_pattern}: {exc}")
        return file_error_response(
            intent,
            FileOperationError(f"Invalid regex pattern: {exc}"),
        )

    # Get file paths to search
    matches = []
    files_searched = 0
    paths = list(
        BASE_DIR.rglob(file_pattern)
        if recursive
        else BASE_DIR.glob(file_pattern)
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
                        lines[i].rstrip("\n\r")
                        for i in range(line_num + 1, end)
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
    data = {
        "pattern": regex_pattern,
        "matches": matches,
        "total_matches": len(matches),
        "files_searched": files_searched,
        "truncated": truncated,
    }
    logger.info(f"Found {len(matches)} matches in {files_searched} files")
    return file_success_response(intent, data)
