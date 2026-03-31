"""Import/export verification for files module public API."""

import aria.tools.files as files_pkg
from aria.tools.files import file_management, unified_read, write_operations


def test_all_exports_present_and_resolvable():
    """All names in __all__ must resolve on package module."""
    for name in files_pkg.__all__:
        assert hasattr(files_pkg, name)


def test_package_exports_point_to_expected_submodules():
    """Package re-exports should map to functions in owning submodule."""
    # Unified read operations
    read_names = {
        "read_file",
        "file_info",
        "list_files",
        "search_files",
    }
    # Unified write operations
    write_names = {
        "write_file",
        "edit_file",
    }
    management_names = {
        "copy_file",
        "delete_file",
        "rename_file",
    }

    for name in read_names:
        assert getattr(files_pkg, name) is getattr(unified_read, name)

    for name in write_names:
        assert getattr(files_pkg, name) is getattr(write_operations, name)

    for name in management_names:
        assert getattr(files_pkg, name) is getattr(file_management, name)
