import json
import shutil
import tempfile
from pathlib import Path

from aria.tools.files.functions import (
    append_to_file,
    copy_file,
    create_directory,
    delete_file,
    delete_lines_range,
    file_exists,
    get_directory_tree,
    get_file_info,
    get_file_permissions,
    insert_lines_at,
    list_files,
    move_file,
    read_file_chunk,
    read_full_file,
    rename_file,
    replace_lines_range,
    search_files_by_name,
    search_in_files,
    write_full_file,
)


class TestFileOperations:
    """Test suite for file operations functions"""

    def setup_method(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.base_dir = Path(self.test_dir)

        # Patch BASE_DIR in all modules that use it
        import aria.tools.files._internals as internals_module
        import aria.tools.files.functions as func_module

        func_module.BASE_DIR = self.base_dir
        internals_module.BASE_DIR = self.base_dir

        # Create some test files and directories
        test_file = self.base_dir / "test.txt"
        test_file.write_text("Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n")

        test_py_file = self.base_dir / "test.py"
        test_py_file.write_text(
            "def hello():\n    print('Hello')\n    return True\n"
        )

        test_dir = self.base_dir / "subdir"
        test_dir.mkdir()
        nested_file = test_dir / "nested.txt"
        nested_file.write_text("Nested content\n")

    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_append_to_file(self):
        """Test appending to file"""
        result = append_to_file(
            "Testing append", str(self.base_dir / "test.txt"), "New line\n"
        )
        data = json.loads(result)

        assert data["operation"] == "append_to_file"
        assert data["result"]["file_name"] == str(self.base_dir / "test.txt")
        assert data["result"]["bytes_appended"] == 9  # "New line\n"
        assert data["result"]["new_total_lines"] == 6

    def test_copy_file(self):
        """Test copying file"""
        result = copy_file(
            "Testing copy",
            str(self.base_dir / "test.txt"),
            str(self.base_dir / "copied.txt"),
        )
        data = json.loads(result)

        assert data["operation"] == "copy_file"
        assert data["result"]["source"] == str(self.base_dir / "test.txt")
        assert data["result"]["destination"] == str(
            self.base_dir / "copied.txt"
        )
        assert (
            data["result"]["bytes_copied"] == 35
        )  # "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"
        assert data["result"]["success"] is True

        # Verify file was copied
        copied_file = self.base_dir / "copied.txt"
        assert copied_file.exists()
        assert (
            copied_file.read_text()
            == "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"
        )

    def test_create_directory(self):
        """Test creating directory"""
        result = create_directory(
            "Testing directory creation",
            str(self.base_dir / "new_dir" / "subdir"),
        )
        data = json.loads(result)

        assert data["operation"] == "create_directory"
        assert data["result"]["dir_name"] == str(
            self.base_dir / "new_dir" / "subdir"
        )
        assert data["result"]["created"] is True

        # Verify directory was created
        new_dir = self.base_dir / "new_dir" / "subdir"
        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_delete_file(self):
        """Test deleting file"""
        result = delete_file(
            "Testing file deletion", str(self.base_dir / "test.txt")
        )
        data = json.loads(result)

        assert data["operation"] == "delete_file"
        assert data["result"]["file_name"] == str(self.base_dir / "test.txt")
        assert data["result"]["deleted"] is True
        assert data["result"]["backup_created"] is True

        # Verify file was deleted and backup created
        assert not (self.base_dir / "test.txt").exists()
        assert (self.base_dir / "test.txt.backup").exists()

    def test_delete_lines_range(self):
        """Test deleting lines range"""
        result = delete_lines_range(
            "Testing line deletion", str(self.base_dir / "test.txt"), 1, 2
        )
        data = json.loads(result)

        assert data["operation"] == "delete_lines_range"
        assert data["result"]["file_name"] == str(self.base_dir / "test.txt")
        assert data["result"]["lines_deleted"] == 2
        assert data["result"]["old_total_lines"] == 5
        assert data["result"]["new_total_lines"] == 3
        assert data["result"]["backup_created"] is True

    def test_file_exists(self):
        """Test checking file existence"""
        result = file_exists(
            "Testing file existence check", str(self.base_dir / "test.txt")
        )
        data = json.loads(result)

        assert data["operation"] == "file_exists"
        assert data["result"]["file_name"] == str(self.base_dir / "test.txt")
        assert data["result"]["exists"] is True
        assert data["result"]["is_file"] is True
        assert data["result"]["is_directory"] is False

        # Test non-existent file
        result = file_exists(
            "Testing non-existent file", str(self.base_dir / "nonexistent.txt")
        )
        data = json.loads(result)
        assert data["result"]["exists"] is False

    def test_get_directory_tree(self):
        """Test getting directory tree"""
        result = get_directory_tree(
            "Testing directory tree", str(self.base_dir)
        )
        data = json.loads(result)

        assert data["operation"] == "get_directory_tree"
        assert data["result"]["path"] == str(self.base_dir)
        assert "tree" in data["result"]
        assert "total_files" in data["result"]
        assert "total_directories" in data["result"]

    def test_get_file_info(self):
        """Test getting file info"""
        result = get_file_info(
            "Testing file info", str(self.base_dir / "test.txt")
        )
        data = json.loads(result)

        assert data["operation"] == "get_file_info"
        assert data["result"]["file_name"] == str(self.base_dir / "test.txt")
        assert data["result"]["total_lines"] == 5
        assert data["result"]["file_size_bytes"] == 35
        assert data["result"]["mime_type"] is not None

    def test_get_file_permissions(self):
        """Test getting file permissions"""
        result = get_file_permissions(
            "Testing file permissions", str(self.base_dir / "test.txt")
        )
        data = json.loads(result)

        assert data["operation"] == "get_file_permissions"
        assert data["result"]["file_name"] == str(self.base_dir / "test.txt")
        assert "mode_octal" in data["result"]
        assert "mode_symbolic" in data["result"]
        assert "permissions" in data["result"]
        assert "is_readable" in data["result"]
        assert "is_writable" in data["result"]
        assert "owner_uid" in data["result"]
        assert "group_gid" in data["result"]

    def test_insert_lines_at(self):
        """Test inserting lines at position"""
        result = insert_lines_at(
            "Testing line insertion",
            str(self.base_dir / "test.txt"),
            ["Inserted line"],
            1,
        )
        data = json.loads(result)

        assert data["operation"] == "insert_lines_at"
        assert data["result"]["file_name"] == str(self.base_dir / "test.txt")
        assert data["result"]["lines_inserted"] == 1
        assert data["result"]["offset"] == 1
        assert data["result"]["new_total_lines"] == 6

    def test_list_files(self):
        """Test listing files"""
        result = list_files("Testing file listing")
        data = json.loads(result)

        assert data["operation"] == "list_files"
        assert data["result"]["pattern"] == "**/*"
        assert len(data["result"]["files"]) >= 1
        assert data["result"]["count"] >= 1

    def test_move_file(self):
        """Test moving file (alias for rename_file)"""
        result = move_file(
            "Testing file move",
            str(self.base_dir / "test.txt"),
            str(self.base_dir / "moved.txt"),
        )
        data = json.loads(result)

        assert data["operation"] == "rename_file"
        assert data["result"]["old_name"] == str(self.base_dir / "test.txt")
        assert data["result"]["new_name"] == str(self.base_dir / "moved.txt")
        assert data["result"]["success"] is True

        # Verify file was moved
        assert not (self.base_dir / "test.txt").exists()
        assert (self.base_dir / "moved.txt").exists()

    def test_read_file_chunk(self):
        """Test reading file chunk"""
        result = read_file_chunk(
            "Testing chunk read",
            str(self.base_dir / "test.txt"),
            chunk_size=2,
            offset=0,
        )
        data = json.loads(result)

        assert data["operation"] == "read_file_chunk"
        assert data["result"]["file_name"] == str(self.base_dir / "test.txt")
        assert len(data["result"]["lines"]) == 2
        assert data["result"]["offset"] == 0
        assert data["result"]["chunk_size"] == 2
        assert data["result"]["lines_returned"] == 2
        assert data["result"]["total_lines"] == 5
        assert data["result"]["has_more"] is True

    def test_read_full_file(self):
        """Test reading full file"""
        result = read_full_file(
            "Testing full file read", str(self.base_dir / "test.txt")
        )
        data = json.loads(result)

        assert data["operation"] == "read_full_file"
        assert data["result"]["file_name"] == str(self.base_dir / "test.txt")
        assert "content" in data["result"]
        assert data["result"]["total_lines"] == 5

    def test_rename_file(self):
        """Test renaming file"""
        result = rename_file(
            "Testing file rename",
            str(self.base_dir / "test.txt"),
            str(self.base_dir / "renamed.txt"),
        )
        data = json.loads(result)

        assert data["operation"] == "rename_file"
        assert data["result"]["old_name"] == str(self.base_dir / "test.txt")
        assert data["result"]["new_name"] == str(self.base_dir / "renamed.txt")
        assert data["result"]["success"] is True

        # Verify file was renamed
        assert not (self.base_dir / "test.txt").exists()
        assert (self.base_dir / "renamed.txt").exists()

    def test_replace_lines_range(self):
        """Test replacing lines range"""
        result = replace_lines_range(
            "Testing line replacement",
            str(self.base_dir / "test.txt"),
            ["New line 1", "New line 2"],
            1,
            2,
        )
        data = json.loads(result)

        assert data["operation"] == "replace_lines_range"
        assert data["result"]["file_name"] == str(self.base_dir / "test.txt")
        assert data["result"]["lines_replaced"] == 2
        assert data["result"]["new_lines_inserted"] == 2
        assert data["result"]["old_total_lines"] == 5
        assert data["result"]["new_total_lines"] == 5
        assert data["result"]["backup_created"] is True

    def test_search_files_by_name(self):
        """Test searching files by name"""
        result = search_files_by_name("Testing file search", r".*\.txt")
        data = json.loads(result)

        assert data["operation"] == "search_files_by_name"
        assert data["result"]["pattern"] == r".*\.txt"
        assert len(data["result"]["matches"]) >= 1
        assert data["result"]["count"] >= 1

    def test_search_in_files(self):
        """Test searching in files"""
        result = search_in_files("Testing content search", r"Line")
        data = json.loads(result)

        assert data["operation"] == "search_in_files"
        assert data["result"]["pattern"] == r"Line"
        assert len(data["result"]["matches"]) >= 1
        assert data["result"]["total_matches"] >= 1
        assert data["result"]["files_searched"] >= 1

    def test_write_full_file(self):
        """Test writing full file"""
        result = write_full_file(
            "Testing file write",
            str(self.base_dir / "new_file.txt"),
            "New content\nSecond line\n",
        )
        data = json.loads(result)

        assert data["operation"] == "write_full_file"
        assert data["result"]["file_name"] == str(
            self.base_dir / "new_file.txt"
        )
        assert (
            data["result"]["bytes_written"] == 24
        )  # "New content\nSecond line\n"
        assert data["result"]["lines_written"] == 2
        assert data["result"]["created"] is True
        assert data["result"]["backup_created"] is False  # No existing file

        # Verify file was written
        new_file = self.base_dir / "new_file.txt"
        assert new_file.exists()
        assert new_file.read_text() == "New content\nSecond line\n"

    def test_write_full_file_with_backup(self):
        """Test writing full file with existing file (backup creation)"""
        # First create a file
        (self.base_dir / "existing.txt").write_text("Original content\n")

        result = write_full_file(
            "Testing file overwrite",
            str(self.base_dir / "existing.txt"),
            "New content\n",
        )
        data = json.loads(result)

        assert data["operation"] == "write_full_file"
        assert (
            data["result"]["backup_created"] is True
        )  # Backup should be created

    def test_write_full_file_exceeds_size_limit(self):
        """Test write_full_file with content exceeding size limit"""
        # Create a large string that exceeds the limit (100MB is the limit)
        large_content = "A" * (100 * 1024 * 1024 + 1)  # Just over 100MB

        result = write_full_file(
            "Testing size limit",
            str(self.base_dir / "large.txt"),
            large_content,
        )
        data = json.loads(result)

        assert data["result"] is None
        assert data["metadata"]["error"] is not None
        assert "exceed" in data["metadata"]["error"].lower()

    def test_read_file_chunk_exceeds_chunk_size(self):
        """Test read_file_chunk with invalid chunk size"""
        result = read_file_chunk(
            "Testing chunk size limit",
            str(self.base_dir / "test.txt"),
            chunk_size=10001,
        )
        data = json.loads(result)

        assert data["result"] is None
        assert data["metadata"]["error"] is not None
        assert "chunk_size" in data["metadata"]["error"].lower()

    def test_search_in_files_invalid_regex(self):
        """Test search_in_files with invalid regex pattern"""
        result = search_in_files("Testing invalid regex", "[")
        data = json.loads(result)
        assert data["metadata"]["error"] is not None

    def test_search_files_by_name_invalid_regex(self):
        """Test search_files_by_name with invalid regex pattern"""
        result = search_files_by_name("Testing invalid regex", "[")
        data = json.loads(result)
        assert data["metadata"]["error"] is not None

    def test_file_operations_with_invalid_paths(self):
        """Test file operations with invalid paths"""
        # These should raise FileOperationError due to security validation
        invalid_paths = [
            "../outside.txt",
            "/etc/passwd",
            "test/../other.txt",
            "test/../../other.txt",
        ]

        for path in invalid_paths:
            append_result = append_to_file(
                "Testing invalid path", path, "test"
            )
            assert json.loads(append_result)["metadata"]["error"] is not None

            read_result = read_file_chunk(
                "Testing invalid path", path, chunk_size=10
            )
            assert json.loads(read_result)["metadata"]["error"] is not None

            write_result = write_full_file(
                "Testing invalid path", path, "test"
            )
            assert json.loads(write_result)["metadata"]["error"] is not None

    def test_append_to_file_with_invalid_path(self):
        """Test append_to_file with invalid path"""
        result = append_to_file(
            "Testing invalid path", "../outside.txt", "test"
        )
        assert json.loads(result)["metadata"]["error"] is not None

    def test_read_file_chunk_with_invalid_path(self):
        """Test read_file_chunk with invalid path"""
        result = read_file_chunk(
            "Testing invalid path", "../outside.txt", chunk_size=10
        )
        assert json.loads(result)["metadata"]["error"] is not None

    def test_write_full_file_with_invalid_path(self):
        """Test write_full_file with invalid path"""
        result = write_full_file(
            "Testing invalid path", "../outside.txt", "test"
        )
        assert json.loads(result)["metadata"]["error"] is not None

    def test_directory_operations_with_invalid_paths(self):
        """Test directory operations with invalid paths"""
        result = create_directory("Testing invalid path", "../outside")
        assert json.loads(result)["metadata"]["error"] is not None

        result = get_directory_tree("Testing invalid path", "../outside")
        assert json.loads(result)["metadata"]["error"] is not None
