"""File operations tools.

Phase 4+5 consolidation: Unified tools replace legacy tools.
"""

# File management operations
from aria.tools.files.file_management import (
    copy_file,
    delete_file,
    rename_file,
)

# Unified read operations (Phase 4)
from aria.tools.files.unified_read import (
    file_info,
    list_files,
    read_file,
    search_files,
)

# Unified write operations (Phase 5)
from aria.tools.files.write_operations import edit_file, write_file

__all__ = [
    # Unified read operations (Phase 4)
    "read_file",
    "file_info",
    "list_files",
    "search_files",
    # Unified write operations (Phase 5)
    "write_file",
    "edit_file",
    # File management
    "copy_file",
    "delete_file",
    "rename_file",
]
