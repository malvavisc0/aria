import json
import shutil
import tempfile
from pathlib import Path

from aria.tools.files import copy_file, delete_file, move_file, rename_file
from aria.tools.files.file_management import copy_file as copy_file_submodule
from aria.tools.files.file_management import (
    delete_file as delete_file_submodule,
)
from aria.tools.files.file_management import move_file as move_file_submodule
from aria.tools.files.file_management import (
    rename_file as rename_file_submodule,
)


class TestFileManagement:
    """Test suite for file management operations."""

    def setup_method(self):
        self.test_dir = tempfile.mkdtemp()
        self.base_dir = Path(self.test_dir)

        import aria.tools.files._internals as internals_module

        internals_module.BASE_DIR = self.base_dir

        test_file = self.base_dir / "test.txt"
        test_file.write_text("Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n")

    def teardown_method(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_package_exports_match_file_management_submodule(self):
        assert copy_file is copy_file_submodule
        assert delete_file is delete_file_submodule
        assert move_file is move_file_submodule
        assert rename_file is rename_file_submodule

    def test_copy_file(self):
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
        assert data["result"]["bytes_copied"] == 35
        assert data["result"]["success"] is True

    def test_delete_file(self):
        result = delete_file(
            "Testing file deletion", str(self.base_dir / "test.txt")
        )
        data = json.loads(result)

        assert data["operation"] == "delete_file"
        assert data["result"]["file_name"] == str(self.base_dir / "test.txt")
        assert data["result"]["deleted"] is True
        assert data["result"]["backup_created"] is True
        assert not (self.base_dir / "test.txt").exists()
        assert (self.base_dir / "test.txt.backup").exists()

    def test_move_file(self):
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

    def test_rename_file(self):
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
