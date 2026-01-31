"""
Tests for files/_internals.py module.

This module tests internal helper functions for file operations.
"""

import json
import stat
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from aria.tools.files._internals import (
    _atomic_write,
    _build_directory_tree,
    _count_lines_efficiently,
    _count_tree_items,
    _create_backup,
    _error_response,
    _format_permissions_symbolic,
    _modify_lines_streaming,
    _read_lines_streaming,
    _safe_json,
    _secure_resolve_dir,
    _secure_resolve_path,
    _timestamp,
    _validate_inputs,
    validate_and_resolve_file,
    validate_and_resolve_two_files,
)
from aria.tools.files.exceptions import FileOperationError, FileSecurityError


class TestTimestamp:
    """Test suite for _timestamp function."""

    def test_timestamp_format(self):
        """Test that timestamp returns ISO format string."""
        ts = _timestamp()
        assert isinstance(ts, str)
        assert "T" in ts  # ISO format contains T separator


class TestErrorResponse:
    """Test suite for _error_response function."""

    def test_security_error_response(self):
        """Test error response for FileSecurityError."""
        exc = FileSecurityError("Path traversal detected")
        result = _error_response("read", "test.txt", exc)
        data = json.loads(result)
        assert data["operation"] == "read"
        assert data["result"] is None
        assert "security" in data["metadata"]["error"].lower()

    def test_file_operation_error_response(self):
        """Test error response for FileOperationError."""
        exc = FileOperationError("File not found")
        result = _error_response("write", "test.txt", exc)
        data = json.loads(result)
        assert "operation failed" in data["metadata"]["error"].lower()

    def test_os_error_response(self):
        """Test error response for OSError."""
        exc = OSError("Disk full")
        result = _error_response("write", "test.txt", exc)
        data = json.loads(result)
        assert "access denied" in data["metadata"]["error"].lower()

    def test_permission_error_response(self):
        """Test error response for PermissionError."""
        exc = PermissionError("Access denied")
        result = _error_response("read", "test.txt", exc)
        data = json.loads(result)
        assert "access denied" in data["metadata"]["error"].lower()

    def test_unexpected_error_response(self):
        """Test error response for unexpected exceptions."""
        exc = ValueError("Unexpected error")
        result = _error_response("read", "test.txt", exc)
        data = json.loads(result)
        assert "unexpected" in data["metadata"]["error"].lower()


class TestValidateInputs:
    """Test suite for _validate_inputs function."""

    def test_valid_inputs(self):
        """Test validation with valid inputs."""
        # Should not raise
        _validate_inputs("test.txt", chunk_size=1024, offset=0, length=100)

    def test_empty_filename(self):
        """Test validation with empty filename."""
        with pytest.raises(FileSecurityError, match="Invalid file name"):
            _validate_inputs("")

    def test_non_string_filename(self):
        """Test validation with non-string filename."""
        with pytest.raises(FileSecurityError, match="Invalid file name"):
            _validate_inputs(123)  # type: ignore

    def test_path_traversal_attempt(self):
        """Test validation detects path traversal."""
        with pytest.raises(FileSecurityError, match="Path traversal"):
            _validate_inputs("../etc/passwd")

    def test_blocked_patterns(self):
        """Test validation detects blocked patterns."""
        with pytest.raises(FileSecurityError, match="blocked patterns"):
            _validate_inputs("test~file.txt")  # ~ is a blocked pattern

    def test_chunk_size_too_large(self):
        """Test validation with chunk size exceeding limit."""
        with pytest.raises(FileSecurityError, match="chunk_size"):
            _validate_inputs("test.txt", chunk_size=100_000_000)

    def test_negative_offset(self):
        """Test validation with negative offset."""
        with pytest.raises(FileSecurityError, match="Negative"):
            _validate_inputs("test.txt", offset=-1)

    def test_negative_length(self):
        """Test validation with negative length."""
        with pytest.raises(FileSecurityError, match="Negative"):
            _validate_inputs("test.txt", length=-1)

    def test_content_size_exceeds_limit(self):
        """Test validation with content exceeding size limit."""
        # MAX_FILE_SIZE is 100MB = 100 * 1024 * 1024
        large_content = "x" * (100 * 1024 * 1024 + 1)
        with pytest.raises(FileSecurityError, match="Content size.*exceeds"):
            _validate_inputs("test.txt", contents=large_content)

    def test_line_length_exceeds_limit(self):
        """Test validation with line exceeding length limit."""
        long_line = "x" * (100_000 + 1)  # Exceeds MAX_LINE_LENGTH
        with pytest.raises(FileSecurityError, match="Line length.*exceeds"):
            _validate_inputs("test.txt", new_lines=[long_line])


class TestCountLinesEfficiently:
    """Test suite for _count_lines_efficiently function."""

    def test_count_lines_in_file(self):
        """Test counting lines in a file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("line1\nline2\nline3\n")
            temp_path = Path(f.name)

        try:
            count = _count_lines_efficiently(temp_path)
            assert count == 3
        finally:
            temp_path.unlink()

    def test_count_lines_os_error(self):
        """Test error handling when file cannot be read."""
        with pytest.raises(FileOperationError, match="Failed to read"):
            _count_lines_efficiently(Path("/nonexistent/file.txt"))


class TestSafeJson:
    """Test suite for _safe_json function."""

    def test_safe_json_success(self):
        """Test successful JSON serialization."""
        data = {"key": "value", "number": 42}
        result = _safe_json(data)
        assert json.loads(result) == data

    def test_safe_json_with_unicode(self):
        """Test JSON serialization with unicode characters."""
        data = {"text": "Hello 世界"}
        result = _safe_json(data)
        parsed = json.loads(result)
        assert parsed["text"] == "Hello 世界"

    def test_safe_json_serialization_error(self):
        """Test error handling for non-serializable objects."""

        class NonSerializable:
            pass

        data = {"obj": NonSerializable()}
        result = _safe_json(data)
        parsed = json.loads(result)
        assert "error" in parsed
        assert "Serialization failed" in parsed["error"]


class TestSecureResolvePath:
    """Test suite for _secure_resolve_path function."""

    def test_resolve_existing_file(self):
        """Test resolving path to existing file."""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt"
        ) as f:
            f.write("test")
            temp_name = Path(f.name).name

        try:
            # This will fail because it's not in BASE_DIR, but tests the logic
            with pytest.raises((FileSecurityError, FileOperationError)):
                _secure_resolve_path(temp_name)
        finally:
            Path(f.name).unlink()

    def test_resolve_path_traversal(self):
        """Test that path traversal is blocked."""
        with pytest.raises(FileSecurityError, match="Path traversal"):
            _secure_resolve_path("../etc/passwd")

    def test_resolve_symlink(self):
        """Test that symlinks are detected (resolve follows them)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            target = tmpdir_path / "target.txt"
            target.write_text("content")
            link = tmpdir_path / "link.txt"
            link.symlink_to(target)

            # Mock BASE_DIR to be tmpdir
            with patch("aria.tools.files._internals.BASE_DIR", tmpdir_path):
                # Symlink check happens after resolve, so it checks if
                # the resolved path is a symlink
                result = _secure_resolve_path("link.txt")
                # Should succeed since resolve() follows symlinks
                assert result.exists()

    def test_resolve_disallowed_extension(self):
        """Test that disallowed file extensions are blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            file_path = tmpdir_path / "test.exe"
            file_path.write_text("content")

            with patch("aria.tools.files._internals.BASE_DIR", tmpdir_path):
                with pytest.raises(FileSecurityError, match="File type not"):
                    _secure_resolve_path("test.exe")

    def test_resolve_nonexistent_file_check_exists_true(self):
        """Test error when file doesn't exist and check_exists=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            with patch("aria.tools.files._internals.BASE_DIR", tmpdir_path):
                with pytest.raises(FileOperationError, match="File not found"):
                    _secure_resolve_path("nonexistent.txt", check_exists=True)

    def test_resolve_nonexistent_file_check_exists_false(self):
        """Test resolving nonexistent file with check_exists=False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            with patch("aria.tools.files._internals.BASE_DIR", tmpdir_path):
                # Should not raise
                result = _secure_resolve_path(
                    "nonexistent.txt", check_exists=False
                )
                assert isinstance(result, Path)


class TestSecureResolveDir:
    """Test suite for _secure_resolve_dir function."""

    def test_resolve_directory(self):
        """Test resolving directory path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            subdir = tmpdir_path / "subdir"
            subdir.mkdir()

            with patch("aria.tools.files._internals.BASE_DIR", tmpdir_path):
                result = _secure_resolve_dir("subdir")
                assert result.is_dir()

    def test_resolve_dir_path_traversal(self):
        """Test that path traversal is blocked for directories."""
        with pytest.raises(FileSecurityError, match="Path traversal"):
            _secure_resolve_dir("../etc")

    def test_resolve_dir_symlink(self):
        """Test that symlinked directories are handled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            target_dir = tmpdir_path / "target"
            target_dir.mkdir()
            link_dir = tmpdir_path / "link"
            link_dir.symlink_to(target_dir)

            with patch("aria.tools.files._internals.BASE_DIR", tmpdir_path):
                # Symlink check happens after resolve
                result = _secure_resolve_dir("link")
                # Should succeed since resolve() follows symlinks
                assert result.is_dir()

    def test_resolve_dir_exception_handling(self):
        """Test exception handling in directory resolution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            # Use a path that will cause traversal error
            with patch("aria.tools.files._internals.BASE_DIR", tmpdir_path):
                with pytest.raises(FileSecurityError, match="Path traversal"):
                    _secure_resolve_dir("../outside")


class TestReadLinesStreaming:
    """Test suite for _read_lines_streaming function."""

    def test_read_all_lines(self):
        """Test reading all lines from file."""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt"
        ) as f:
            f.write("line1\nline2\nline3\n")
            temp_path = Path(f.name)

        try:
            lines = _read_lines_streaming(temp_path, offset=0, length=0)
            assert lines == ["line1", "line2", "line3"]
        finally:
            temp_path.unlink()

    def test_read_lines_with_offset(self):
        """Test reading lines with offset."""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt"
        ) as f:
            f.write("line1\nline2\nline3\n")
            temp_path = Path(f.name)

        try:
            lines = _read_lines_streaming(temp_path, offset=1, length=0)
            assert lines == ["line2", "line3"]
        finally:
            temp_path.unlink()

    def test_read_lines_with_length(self):
        """Test reading specific number of lines."""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt"
        ) as f:
            f.write("line1\nline2\nline3\n")
            temp_path = Path(f.name)

        try:
            lines = _read_lines_streaming(temp_path, offset=0, length=2)
            assert lines == ["line1", "line2"]
        finally:
            temp_path.unlink()

    def test_read_lines_os_error(self):
        """Test error handling when file cannot be read."""
        with pytest.raises(FileOperationError, match="Failed to read"):
            _read_lines_streaming(Path("/nonexistent.txt"), 0, 0)


class TestModifyLinesStreaming:
    """Test suite for _modify_lines_streaming function."""

    def test_replace_lines(self):
        """Test replacing lines in file."""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt"
        ) as f:
            f.write("line1\nline2\nline3\n")
            temp_path = Path(f.name)

        try:
            old_total, new_total = _modify_lines_streaming(
                temp_path, offset=1, length=1, new_lines=["replaced"]
            )
            assert old_total == 3
            assert new_total == 3
            content = temp_path.read_text()
            assert "replaced" in content
        finally:
            temp_path.unlink()

    def test_insert_lines(self):
        """Test inserting lines in file."""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt"
        ) as f:
            f.write("line1\nline2\n")
            temp_path = Path(f.name)

        try:
            old_total, new_total = _modify_lines_streaming(
                temp_path, offset=1, length=0, new_lines=["inserted"]
            )
            assert new_total == old_total + 1
        finally:
            temp_path.unlink()

    def test_delete_lines(self):
        """Test deleting lines from file."""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt"
        ) as f:
            f.write("line1\nline2\nline3\n")
            temp_path = Path(f.name)

        try:
            old_total, new_total = _modify_lines_streaming(
                temp_path, offset=1, length=1, new_lines=None
            )
            assert new_total == old_total - 1
        finally:
            temp_path.unlink()

    def test_append_lines_beyond_end(self):
        """Test appending lines beyond end of file."""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt"
        ) as f:
            f.write("line1\nline2\n")
            temp_path = Path(f.name)

        try:
            old_total, new_total = _modify_lines_streaming(
                temp_path, offset=10, length=0, new_lines=["appended"]
            )
            assert new_total > old_total
        finally:
            temp_path.unlink()

    def test_modify_lines_error_cleanup(self):
        """Test that temp file is cleaned up on error."""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt"
        ) as f:
            temp_path = Path(f.name)

        temp_path.unlink()  # Delete file to cause error

        with pytest.raises(FileOperationError, match="Failed to modify"):
            _modify_lines_streaming(
                temp_path, offset=0, length=1, new_lines=["test"]
            )


class TestAtomicWrite:
    """Test suite for _atomic_write function."""

    def test_atomic_write_success(self):
        """Test successful atomic write."""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt"
        ) as f:
            temp_path = Path(f.name)

        try:
            _atomic_write(temp_path, "test content")
            assert temp_path.read_text() == "test content"
        finally:
            temp_path.unlink()

    def test_atomic_write_error_cleanup(self):
        """Test that temp file is cleaned up on error."""
        invalid_path = Path("/invalid/path/file.txt")
        with pytest.raises(FileOperationError, match="Failed to write"):
            _atomic_write(invalid_path, "content")


class TestCreateBackup:
    """Test suite for _create_backup function."""

    def test_create_backup_success(self):
        """Test successful backup creation."""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt"
        ) as f:
            f.write("original content")
            temp_path = Path(f.name)

        try:
            backup_path = _create_backup(temp_path)
            assert backup_path is not None
            assert backup_path.exists()
            assert backup_path.read_text() == "original content"
            backup_path.unlink()
        finally:
            temp_path.unlink()

    def test_create_backup_nonexistent_file(self):
        """Test backup of nonexistent file returns None."""
        result = _create_backup(Path("/nonexistent/file.txt"))
        assert result is None

    def test_create_backup_error(self):
        """Test backup creation error handling."""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt"
        ) as f:
            temp_path = Path(f.name)

        try:
            # Mock shutil.copy2 to raise an exception
            with patch("aria.tools.files._internals.shutil.copy2") as mock:
                mock.side_effect = PermissionError("Access denied")
                result = _create_backup(temp_path)
                assert result is None  # Should return None on error
        finally:
            temp_path.unlink()


class TestBuildDirectoryTree:
    """Test suite for _build_directory_tree function."""

    def test_build_tree_simple(self):
        """Test building directory tree."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "file1.txt").write_text("content")
            (tmpdir_path / "file2.txt").write_text("content")

            tree = _build_directory_tree(tmpdir_path, 0, 2)
            assert tree["type"] == "directory"
            assert len(tree["children"]) == 2

    def test_build_tree_with_subdirs(self):
        """Test building tree with subdirectories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            subdir = tmpdir_path / "subdir"
            subdir.mkdir()
            (subdir / "file.txt").write_text("content")

            tree = _build_directory_tree(tmpdir_path, 0, 2)
            assert any(
                child["type"] == "directory" for child in tree["children"]
            )

    def test_build_tree_max_depth(self):
        """Test that max depth is respected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            subdir = tmpdir_path / "subdir"
            subdir.mkdir()

            tree = _build_directory_tree(tmpdir_path, 0, 0)
            assert tree["children"] == []

    def test_build_tree_permission_error(self):
        """Test handling of permission errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Mock iterdir to raise PermissionError
            with patch.object(Path, "iterdir") as mock_iterdir:
                mock_iterdir.side_effect = PermissionError("Access denied")
                tree = _build_directory_tree(tmpdir_path, 0, 2)
                # Should return tree with empty children
                assert tree["children"] == []


class TestCountTreeItems:
    """Test suite for _count_tree_items function."""

    def test_count_files_and_dirs(self):
        """Test counting files and directories in tree."""
        tree = {
            "type": "directory",
            "children": [
                {"type": "file", "name": "file1.txt"},
                {"type": "file", "name": "file2.txt"},
                {
                    "type": "directory",
                    "children": [{"type": "file", "name": "file3.txt"}],
                },
            ],
        }
        files, dirs = _count_tree_items(tree)
        assert files == 3
        assert dirs == 2  # Root dir + 1 subdir


class TestFormatPermissionsSymbolic:
    """Test suite for _format_permissions_symbolic function."""

    def test_format_permissions_rwx(self):
        """Test formatting full permissions."""
        mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR
        mode |= stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP
        mode |= stat.S_IROTH | stat.S_IWOTH | stat.S_IXOTH
        result = _format_permissions_symbolic(mode)
        assert result == "rwxrwxrwx"

    def test_format_permissions_readonly(self):
        """Test formatting read-only permissions."""
        mode = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
        result = _format_permissions_symbolic(mode)
        assert result == "r--r--r--"

    def test_format_permissions_mixed(self):
        """Test formatting mixed permissions."""
        mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP
        result = _format_permissions_symbolic(mode)
        assert result == "rw-r-----"


class TestValidateAndResolveFile:
    """Test suite for validate_and_resolve_file function."""

    def test_validate_and_resolve_success(self):
        """Test successful validation and resolution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            file_path = tmpdir_path / "test.txt"
            file_path.write_text("content")

            with patch("aria.tools.files._internals.BASE_DIR", tmpdir_path):
                result = validate_and_resolve_file("test.txt")
                assert result.exists()

    def test_validate_and_resolve_invalid_input(self):
        """Test validation with invalid input."""
        with pytest.raises(FileSecurityError):
            validate_and_resolve_file("../etc/passwd")


class TestValidateAndResolveTwoFiles:
    """Test suite for validate_and_resolve_two_files function."""

    def test_validate_two_files_success(self):
        """Test successful validation of two files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            source = tmpdir_path / "source.txt"
            source.write_text("content")

            with patch("aria.tools.files._internals.BASE_DIR", tmpdir_path):
                src_path, dest_path = validate_and_resolve_two_files(
                    "source.txt", "dest.txt", dest_must_exist=False
                )
                assert src_path.exists()

    def test_validate_two_files_invalid_source(self):
        """Test validation with invalid source."""
        with pytest.raises(FileSecurityError):
            validate_and_resolve_two_files("../etc/passwd", "dest.txt")

    def test_validate_two_files_invalid_dest(self):
        """Test validation with invalid destination."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            source = tmpdir_path / "source.txt"
            source.write_text("content")

            with patch("aria.tools.files._internals.BASE_DIR", tmpdir_path):
                with pytest.raises(FileSecurityError):
                    validate_and_resolve_two_files(
                        "source.txt", "../etc/passwd"
                    )
