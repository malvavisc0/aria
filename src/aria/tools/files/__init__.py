"""File operations tools."""

from aria.tools.files.file_management import (
    copy_file,
    delete_file,
    move_file,
    rename_file,
)
from aria.tools.files.read_operations import (
    file_exists,
    get_directory_tree,
    get_file_info,
    get_file_permissions,
    list_files,
    read_file_chunk,
    read_full_file,
    search_files_by_name,
    search_in_files,
)
from aria.tools.files.write_operations import (
    append_to_file,
    create_directory,
    delete_lines_range,
    insert_lines_at,
    replace_lines_range,
    write_full_file,
)

__all__ = [
    # Read operations
    "file_exists",
    "get_directory_tree",
    "get_file_info",
    "get_file_permissions",
    "list_files",
    "read_file_chunk",
    "read_full_file",
    "search_files_by_name",
    "search_in_files",
    # Write operations
    "append_to_file",
    "create_directory",
    "delete_lines_range",
    "insert_lines_at",
    "replace_lines_range",
    "write_full_file",
    # File management
    "copy_file",
    "delete_file",
    "move_file",
    "rename_file",
]
