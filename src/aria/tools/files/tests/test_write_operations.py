import json
import shutil
import tempfile
from pathlib import Path

from aria.tools.files import (
    append_to_file,
    create_directory,
    delete_lines_range,
    insert_lines_at,
    replace_lines_range,
    write_full_file,
)
from aria.tools.files.write_operations import (
    append_to_file as append_to_file_submodule,
)
from aria.tools.files.write_operations import (
    create_directory as create_directory_submodule,
)
from aria.tools.files.write_operations import (
    delete_lines_range as delete_lines_range_submodule,
)
from aria.tools.files.write_operations import (
    insert_lines_at as insert_lines_at_submodule,
)
from aria.tools.files.write_operations import (
    replace_lines_range as replace_lines_range_submodule,
)
from aria.tools.files.write_operations import (
    write_full_file as write_full_file_submodule,
)


class TestWriteOperations:
    """Test suite for write and content-modification file operations."""

    def setup_method(self):
        self.test_dir = tempfile.mkdtemp()
        self.base_dir = Path(self.test_dir)

        import aria.tools.files._internals as internals_module

        internals_module.BASE_DIR = self.base_dir

        test_file = self.base_dir / "test.txt"
        test_file.write_text("Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n")

    def teardown_method(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_package_exports_match_write_submodule(self):
        assert append_to_file is append_to_file_submodule
        assert create_directory is create_directory_submodule
        assert delete_lines_range is delete_lines_range_submodule
        assert insert_lines_at is insert_lines_at_submodule
        assert replace_lines_range is replace_lines_range_submodule
        assert write_full_file is write_full_file_submodule

    def test_append_to_file(self):
        result = append_to_file(
            "Testing append", str(self.base_dir / "test.txt"), "New line\n"
        )
        data = json.loads(result)

        assert data["tool"] == "append_to_file"
        assert data["data"]["file_name"] == str(self.base_dir / "test.txt")
        assert data["data"]["bytes_appended"] == 9
        assert data["data"]["new_total_lines"] == 6

    def test_create_directory(self):
        result = create_directory(
            "Testing directory creation",
            str(self.base_dir / "new_dir" / "subdir"),
        )
        data = json.loads(result)

        assert data["tool"] == "create_directory"
        assert data["data"]["dir_name"] == str(
            self.base_dir / "new_dir" / "subdir"
        )
        assert data["data"]["created"] is True

    def test_delete_lines_range(self):
        result = delete_lines_range(
            "Testing line deletion", str(self.base_dir / "test.txt"), 1, 2
        )
        data = json.loads(result)

        assert data["tool"] == "delete_lines_range"
        assert data["data"]["lines_deleted"] == 2
        assert data["data"]["old_total_lines"] == 5
        assert data["data"]["new_total_lines"] == 3
        assert data["data"]["backup_created"] is True

    def test_insert_lines_at(self):
        result = insert_lines_at(
            "Testing line insertion",
            str(self.base_dir / "test.txt"),
            ["Inserted line"],
            1,
        )
        data = json.loads(result)

        assert data["tool"] == "insert_lines_at"
        assert data["data"]["lines_inserted"] == 1
        assert data["data"]["offset"] == 1
        assert data["data"]["new_total_lines"] == 6

    def test_replace_lines_range(self):
        result = replace_lines_range(
            "Testing line replacement",
            str(self.base_dir / "test.txt"),
            ["New line 1", "New line 2"],
            1,
            2,
        )
        data = json.loads(result)

        assert data["tool"] == "replace_lines_range"
        assert data["data"]["lines_replaced"] == 2
        assert data["data"]["new_lines_inserted"] == 2
        assert data["data"]["old_total_lines"] == 5
        assert data["data"]["new_total_lines"] == 5
        assert data["data"]["backup_created"] is True

    def test_write_full_file(self):
        result = write_full_file(
            "Testing file write",
            str(self.base_dir / "new_file.txt"),
            "New content\nSecond line\n",
        )
        data = json.loads(result)

        assert data["tool"] == "write_full_file"
        assert data["data"]["file_name"] == str(self.base_dir / "new_file.txt")
        assert data["data"]["bytes_written"] == 24
        assert data["data"]["lines_written"] == 2
        assert data["data"]["created"] is True
        assert data["data"]["backup_created"] is False

        new_file = self.base_dir / "new_file.txt"
        assert new_file.exists()
        assert new_file.read_text() == "New content\nSecond line\n"

    def test_write_full_file_with_backup(self):
        (self.base_dir / "existing.txt").write_text("Original content\n")

        result = write_full_file(
            "Testing file overwrite",
            str(self.base_dir / "existing.txt"),
            "New content\n",
        )
        data = json.loads(result)

        assert data["tool"] == "write_full_file"
        assert data["data"]["backup_created"] is True

    def test_write_full_file_exceeds_size_limit(self):
        large_content = "A" * (100 * 1024 * 1024 + 1)

        result = write_full_file(
            "Testing size limit",
            str(self.base_dir / "large.txt"),
            large_content,
        )
        data = json.loads(result)

        assert data["status"] == "error"
        assert "exceed" in data["error"]["message"].lower()

    def test_write_operations_with_invalid_paths(self):
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
            assert json.loads(append_result)["status"] == "error"

            write_result = write_full_file(
                "Testing invalid path", path, "test"
            )
            assert json.loads(write_result)["status"] == "error"

    def test_append_to_file_with_invalid_path(self):
        result = append_to_file(
            "Testing invalid path", "../outside.txt", "test"
        )
        assert json.loads(result)["status"] == "error"

    def test_write_full_file_with_invalid_path(self):
        result = write_full_file(
            "Testing invalid path", "../outside.txt", "test"
        )
        assert json.loads(result)["status"] == "error"

    def test_write_full_file_lines_written_empty(self):
        """Empty content should report 0 lines written."""
        result = write_full_file(
            "Testing empty file",
            str(self.base_dir / "empty.txt"),
            "",
        )
        data = json.loads(result)
        assert data["data"]["lines_written"] == 0
        assert data["data"]["bytes_written"] == 0

    def test_write_full_file_lines_written_single_no_newline(self):
        """Single line without trailing newline should report 1 line."""
        content = "Single line content"
        result = write_full_file(
            "Testing single line",
            str(self.base_dir / "single.txt"),
            content,
        )
        data = json.loads(result)
        assert data["data"]["lines_written"] == 1
        assert data["data"]["bytes_written"] == len(content.encode("utf-8"))

    def test_write_full_file_lines_written_single_with_newline(self):
        """Single line with trailing newline should report 1 line."""
        content = "Single line content\n"
        result = write_full_file(
            "Testing single line with newline",
            str(self.base_dir / "single_newline.txt"),
            content,
        )
        data = json.loads(result)
        assert data["data"]["lines_written"] == 1

    def test_write_full_file_lines_written_multiple_no_trailing_newline(self):
        """Multiple lines without trailing newline count as newlines + 1."""
        content = "Line 1\nLine 2\nLine 3"
        result = write_full_file(
            "Testing multiple lines",
            str(self.base_dir / "multi.txt"),
            content,
        )
        data = json.loads(result)
        # 2 newlines + 1 = 3 lines
        assert data["data"]["lines_written"] == 3
        assert data["data"]["bytes_written"] == len(content.encode("utf-8"))

    def test_write_full_file_lines_written_only_newlines(self):
        """Content with only newlines should count newline characters."""
        content = "\n\n\n"
        result = write_full_file(
            "Testing only newlines",
            str(self.base_dir / "newlines.txt"),
            content,
        )
        data = json.loads(result)
        # 3 newline characters = 3 lines
        assert data["data"]["lines_written"] == 3

    def test_write_full_file_lines_written_crlf(self):
        """Content with CRLF line endings should count correctly."""
        content = "Line 1\r\nLine 2\r\nLine 3\r\n"
        result = write_full_file(
            "Testing CRLF",
            str(self.base_dir / "crlf.txt"),
            content,
        )
        data = json.loads(result)
        # Should count \n characters, not \r\n pairs
        # \n\n\n results in 3 lines when there's trailing content
        assert data["data"]["lines_written"] == 3

    def test_write_full_file_bytes_written_utf8(self):
        """UTF-8 content with non-ASCII chars should count bytes correctly."""
        content = "Hello 你好 🌍\n"
        result = write_full_file(
            "Testing UTF-8",
            str(self.base_dir / "utf8.txt"),
            content,
        )
        data = json.loads(result)
        assert data["data"]["bytes_written"] == len(content.encode("utf-8"))
        assert data["data"]["lines_written"] == 1

    def test_directory_operations_with_invalid_paths(self):
        result = create_directory("Testing invalid path", "../outside")
        assert json.loads(result)["status"] == "error"
