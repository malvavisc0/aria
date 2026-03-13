"""Import/export verification for files module public API."""

import aria.tools.files as files_pkg
from aria.tools.files import file_management, read_operations, write_operations


def test_all_exports_present_and_resolvable():
    """All names in __all__ must resolve on package module."""
    for name in files_pkg.__all__:
        assert hasattr(files_pkg, name)


def test_package_exports_point_to_expected_submodules():
    """Package re-exports should map to functions in owning submodule."""
    read_names = {
        "file_exists",
        "get_directory_tree",
        "get_file_info",
        "get_file_permissions",
        "list_files",
        "read_file_chunk",
        "read_full_file",
        "search_files_by_name",
        "search_in_files",
    }
    write_names = {
        "append_to_file",
        "create_directory",
        "delete_lines_range",
        "insert_lines_at",
        "replace_lines_range",
        "write_full_file",
    }
    management_names = {
        "copy_file",
        "delete_file",
        "move_file",
        "rename_file",
    }

    for name in read_names:
        assert getattr(files_pkg, name) is getattr(read_operations, name)

    for name in write_names:
        assert getattr(files_pkg, name) is getattr(write_operations, name)

    for name in management_names:
        assert getattr(files_pkg, name) is getattr(file_management, name)


def test_export_count_matches_phase4_contract():
    """Phase 4 contract exports exactly 19 public operations."""
    assert len(files_pkg.__all__) == 19
