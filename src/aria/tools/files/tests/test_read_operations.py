import json
import shutil
import tempfile
from pathlib import Path

from aria.tools.files import (
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
from aria.tools.files.read_operations import (
    file_exists as file_exists_submodule,
)
from aria.tools.files.read_operations import (
    get_directory_tree as get_directory_tree_submodule,
)
from aria.tools.files.read_operations import (
    get_file_info as get_file_info_submodule,
)
from aria.tools.files.read_operations import (
    get_file_permissions as get_file_permissions_submodule,
)
from aria.tools.files.read_operations import list_files as list_files_submodule
from aria.tools.files.read_operations import (
    read_file_chunk as read_file_chunk_submodule,
)
from aria.tools.files.read_operations import (
    read_full_file as read_full_file_submodule,
)
from aria.tools.files.read_operations import (
    search_files_by_name as search_files_by_name_submodule,
)
from aria.tools.files.read_operations import (
    search_in_files as search_in_files_submodule,
)


class TestReadOperations:
    """Test suite for read-only file operation functions."""

    def setup_method(self):
        self.test_dir = tempfile.mkdtemp()
        self.base_dir = Path(self.test_dir)

        # Patch BASE_DIR in modules that read operations depend on
        import aria.tools.files._internals as internals_module
        import aria.tools.files.read_operations as read_ops_module

        read_ops_module.BASE_DIR = self.base_dir
        internals_module.BASE_DIR = self.base_dir

        # Test fixtures
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
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_package_exports_match_read_submodule(self):
        assert file_exists is file_exists_submodule
        assert get_directory_tree is get_directory_tree_submodule
        assert get_file_info is get_file_info_submodule
        assert get_file_permissions is get_file_permissions_submodule
        assert list_files is list_files_submodule
        assert read_file_chunk is read_file_chunk_submodule
        assert read_full_file is read_full_file_submodule
        assert search_files_by_name is search_files_by_name_submodule
        assert search_in_files is search_in_files_submodule

    def test_file_exists(self):
        result = file_exists(
            "Testing file existence check", str(self.base_dir / "test.txt")
        )
        data = json.loads(result)

        assert data["operation"] == "file_exists"
        assert data["result"]["file_name"] == str(self.base_dir / "test.txt")
        assert data["result"]["exists"] is True
        assert data["result"]["is_file"] is True
        assert data["result"]["is_directory"] is False

        result = file_exists(
            "Testing non-existent file", str(self.base_dir / "nonexistent.txt")
        )
        data = json.loads(result)
        assert data["result"]["exists"] is False

    def test_get_directory_tree(self):
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

    def test_list_files(self):
        result = list_files("Testing file listing")
        data = json.loads(result)

        assert data["operation"] == "list_files"
        assert data["result"]["pattern"] == "**/*"
        assert len(data["result"]["files"]) >= 1
        assert data["result"]["count"] >= 1

    def test_read_file_chunk(self):
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
        assert data["result"]["total_lines"] == 5
        assert data["result"]["has_more"] is True

    def test_read_full_file(self):
        result = read_full_file(
            "Testing full file read", str(self.base_dir / "test.txt")
        )
        data = json.loads(result)

        assert data["operation"] == "read_full_file"
        assert data["result"]["file_name"] == str(self.base_dir / "test.txt")
        assert "content" in data["result"]
        assert data["result"]["total_lines"] == 5

    def test_search_files_by_name(self):
        result = search_files_by_name("Testing file search", r".*\.txt")
        data = json.loads(result)

        assert data["operation"] == "search_files_by_name"
        assert data["result"]["pattern"] == r".*\.txt"
        assert len(data["result"]["matches"]) >= 1

    def test_search_in_files(self):
        result = search_in_files("Testing content search", r"Line")
        data = json.loads(result)

        assert data["operation"] == "search_in_files"
        assert data["result"]["pattern"] == r"Line"
        assert len(data["result"]["matches"]) >= 1
        assert data["result"]["total_matches"] >= 1

    def test_read_file_chunk_exceeds_chunk_size(self):
        result = read_file_chunk(
            "Testing chunk size limit",
            str(self.base_dir / "test.txt"),
            chunk_size=10001,
        )
        data = json.loads(result)

        assert data["status"] == "error"
        assert "chunk_size" in data["error"]["message"].lower()

    def test_search_in_files_invalid_regex(self):
        result = search_in_files("Testing invalid regex", "[")
        data = json.loads(result)
        assert data["status"] == "error"
        assert data["error"] is not None

    def test_search_files_by_name_invalid_regex(self):
        result = search_files_by_name("Testing invalid regex", "[")
        data = json.loads(result)
        assert data["status"] == "error"
        assert data["error"] is not None

    def test_read_operations_with_invalid_paths(self):
        invalid_paths = [
            "../outside.txt",
            "/etc/passwd",
            "test/../other.txt",
            "test/../../other.txt",
        ]

        for path in invalid_paths:
            read_result = read_file_chunk(
                "Testing invalid path", path, chunk_size=10
            )
            assert json.loads(read_result)["status"] == "error"

    def test_directory_operations_with_invalid_paths(self):
        result = get_directory_tree("Testing invalid path", "../outside")
        assert json.loads(result)["status"] == "error"
