"""Behavioral contract tests for files module.

This module addresses issue #15 from the tools audit: tests should verify
actual behavior, not just export presence. These tests verify:
1. Functions return JSON as documented
2. Error responses have consistent structure
3. Path handling behavior matches documentation

Run with: pytest src/aria/tools/files/tests/test_behavioral_contract.py -v
"""

import inspect
import json
import shutil
import tempfile
from pathlib import Path

from aria.tools.files import (
    append_to_file,
    read_full_file,
    read_operations,
    write_full_file,
)


class TestFilesReturnJsonContract:
    """Verify file operations return JSON responses."""

    def setup_method(self):
        self.test_dir = tempfile.mkdtemp()
        self.base_dir = Path(self.test_dir)
        import aria.tools.files._internals as internals_module

        internals_module.BASE_DIR = self.base_dir

    def teardown_method(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_write_full_file_returns_json(self):
        """write_full_file should return valid JSON with documented fields."""
        result = write_full_file(
            "Testing",
            str(self.base_dir / "test.txt"),
            "content",
        )
        data = json.loads(result)
        # Verify required fields in actual format
        assert "operation" in data
        assert "result" in data
        assert "metadata" in data

    def test_read_full_file_returns_json(self):
        """read_full_file should return valid JSON response."""
        test_file = self.base_dir / "read_test.txt"
        test_file.write_text("test content\n")

        result = read_full_file(
            "Testing",
            str(self.base_dir / "read_test.txt"),
        )
        data = json.loads(result)
        assert "operation" in data
        assert "result" in data

    def test_append_to_file_returns_json(self):
        """append_to_file should return valid JSON response."""
        test_file = self.base_dir / "append_test.txt"
        test_file.write_text("initial\n")

        result = append_to_file(
            "Testing",
            str(self.base_dir / "append_test.txt"),
            "added\n",
        )
        data = json.loads(result)
        assert "operation" in data
        assert "result" in data


class TestFilesErrorResponseContract:
    """Verify error responses have consistent structure."""

    def setup_method(self):
        self.test_dir = tempfile.mkdtemp()
        self.base_dir = Path(self.test_dir)
        import aria.tools.files._internals as internals_module

        internals_module.BASE_DIR = self.base_dir

    def teardown_method(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_invalid_path_returns_error_status(self):
        """Invalid paths should return error status."""
        result = write_full_file(
            "Testing",
            "/etc/passwd",
            "malicious",
        )
        data = json.loads(result)
        assert data["status"] == "error"
        assert "error" in data
        assert "message" in data["error"]

    def test_nonexistent_file_read_returns_error(self):
        """Reading nonexistent file should return error status."""
        result = read_full_file(
            "Testing",
            str(self.base_dir / "nonexistent.txt"),
        )
        data = json.loads(result)
        assert data["status"] == "error"


class TestListFilesParameterNaming:
    """Issue #1: Verify list_files has correct parameter naming.

    The audit found that inventory documented 'dir_name' but implementation
    uses 'pattern', 'recursive', 'max_results'.
    """

    def test_list_files_has_pattern_parameter(self):
        """list_files should have 'pattern' parameter."""
        sig = inspect.signature(read_operations.list_files)
        params = list(sig.parameters.keys())
        assert (
            "pattern" in params
        ), f"list_files should have 'pattern' parameter, got {params}"

    def test_list_files_has_recursive_parameter(self):
        """list_files should have 'recursive' parameter."""
        sig = inspect.signature(read_operations.list_files)
        params = list(sig.parameters.keys())
        assert "recursive" in params

    def test_list_files_has_max_results_parameter(self):
        """list_files should have 'max_results' parameter."""
        sig = inspect.signature(read_operations.list_files)
        params = list(sig.parameters.keys())
        assert "max_results" in params


class TestReadFileChunkParameterNaming:
    """Issue #2: Verify read_file_chunk uses correct parameter names."""

    def test_read_file_chunk_has_chunk_size_parameter(self):
        """read_file_chunk should have 'chunk_size' not 'length' param."""
        sig = inspect.signature(read_operations.read_file_chunk)
        params = list(sig.parameters.keys())
        assert (
            "chunk_size" in params
        ), f"read_file_chunk should have 'chunk_size' parameter, got {params}"
        assert (
            "length" not in params
        ), "read_file_chunk should NOT have 'length' parameter"


class TestSearchFilesByNameContract:
    """Issue #9: Verify search_files_by_name parameter naming.

    The audit found docs described glob but implementation uses regex.
    """

    def test_search_files_by_name_has_regex_pattern(self):
        """search_files_by_name should have 'regex_pattern' parameter."""
        sig = inspect.signature(read_operations.search_files_by_name)
        params = list(sig.parameters.keys())
        assert (
            "regex_pattern" in params
        ), f"search_files_by_name should have 'regex_pattern', got {params}"
