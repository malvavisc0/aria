"""Tests for download and extraction functions in llama.py."""

import tarfile
import tempfile
import urllib.error
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from aria.scripts.llama import _download_and_extract, _download_and_extract_zip


class TestDownloadAndExtractZip:
    """Tests for _download_and_extract_zip() function."""

    def test_downloads_and_extract_zip_success(self, tmp_path: Path):
        """Test that _download_and_extract_zip downloads and extracts zip successfully."""
        # Create a temporary zip file
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("llama.cpp-v1.2.3/README.md", "test content")
                zf.writestr("llama.cpp-v1.2.3/CMakeLists.txt", "cmake content")

            # Mock urlretrieve to return our zip file
            with patch("urllib.request.urlretrieve") as mock_retrieve:
                mock_retrieve.side_effect = (
                    lambda url, path, reporthook=None: Path(path).write_bytes(
                        zip_path.read_bytes()
                    )
                )

                dest_dir = tmp_path / "extracted"
                result = _download_and_extract_zip(
                    "https://example.com/test.zip", dest_dir
                )

                assert result.is_dir()
                assert result.name == "llama.cpp-v1.2.3"
                assert (result / "README.md").exists()
                assert (result / "CMakeLists.txt").exists()

    def test_returns_first_subdirectory(self, tmp_path: Path):
        """Test that _download_and_extract_zip returns first subdirectory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("llama.cpp-v1.2.3/README.md", "test content")
                zf.writestr(
                    "llama.cpp-v1.2.3/build/README.md", "build content"
                )

            with patch("urllib.request.urlretrieve") as mock_retrieve:
                mock_retrieve.side_effect = (
                    lambda url, path, reporthook=None: Path(path).write_bytes(
                        zip_path.read_bytes()
                    )
                )

                dest_dir = tmp_path / "extracted"
                result = _download_and_extract_zip(
                    "https://example.com/test.zip", dest_dir
                )

                assert result.name == "llama.cpp-v1.2.3"

    def test_creates_destination_directory(self, tmp_path: Path):
        """Test that _download_and_extract_zip creates destination directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("llama.cpp-v1.2.3/README.md", "test content")

            with patch("urllib.request.urlretrieve") as mock_retrieve:
                mock_retrieve.side_effect = (
                    lambda url, path, reporthook=None: Path(path).write_bytes(
                        zip_path.read_bytes()
                    )
                )

                dest_dir = tmp_path / "new" / "directory"
                result = _download_and_extract_zip(
                    "https://example.com/test.zip", dest_dir
                )

                assert dest_dir.exists()
                assert result.is_dir()

    def test_handles_empty_zip(self, tmp_path: Path):
        """Test that _download_and_extract_zip handles empty zip."""
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "empty.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                pass  # Empty zip

            with patch("urllib.request.urlretrieve") as mock_retrieve:
                mock_retrieve.side_effect = (
                    lambda url, path, reporthook=None: Path(path).write_bytes(
                        zip_path.read_bytes()
                    )
                )

                dest_dir = tmp_path / "extracted"
                result = _download_and_extract_zip(
                    "https://example.com/empty.zip", dest_dir
                )

                # Should return dest_dir when no subdirectories
                assert result == dest_dir

    def test_raises_url_error_on_network_failure(self, tmp_path: Path):
        """Test that _download_and_extract_zip raises URLError on network failure."""
        with patch("urllib.request.urlretrieve") as mock_retrieve:
            mock_retrieve.side_effect = urllib.error.URLError("Network error")

            with pytest.raises(urllib.error.URLError):
                _download_and_extract_zip(
                    "https://example.com/test.zip", tmp_path / "extracted"
                )


class TestDownloadAndExtract:
    """Tests for _download_and_extract() function."""

    def test_downloads_and_extract_tar_gz_success(self, tmp_path: Path):
        """Test that _download_and_extract downloads and extracts tar.gz successfully."""
        # Create a temporary tar.gz file
        with tempfile.TemporaryDirectory() as tmpdir:
            tar_path = Path(tmpdir) / "test.tar.gz"
            with tarfile.open(tar_path, "w:gz") as tf:
                # Create a test file
                test_file = Path(tmpdir) / "test.txt"
                test_file.write_text("test content")
                tf.add(test_file, arcname="llama.cpp-v1.2.3/README.md")

            # Mock urlretrieve to return our tar.gz file
            with patch("urllib.request.urlretrieve") as mock_retrieve:
                mock_retrieve.side_effect = (
                    lambda url, path, reporthook=None: Path(path).write_bytes(
                        tar_path.read_bytes()
                    )
                )

                dest_dir = tmp_path / "extracted"
                result = _download_and_extract(
                    "https://example.com/test.tar.gz", dest_dir
                )

                assert len(result) > 0
                assert (dest_dir / "llama.cpp-v1.2.3" / "README.md").exists()

    def test_returns_list_of_extracted_files(self, tmp_path: Path):
        """Test that _download_and_extract returns list of extracted file paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tar_path = Path(tmpdir) / "test.tar.gz"
            with tarfile.open(tar_path, "w:gz") as tf:
                test_file = Path(tmpdir) / "test.txt"
                test_file.write_text("test content")
                tf.add(test_file, arcname="llama.cpp-v1.2.3/README.md")

                test_file2 = Path(tmpdir) / "test2.txt"
                test_file2.write_text("test content 2")
                tf.add(test_file2, arcname="llama.cpp-v1.2.3/CMakeLists.txt")

            with patch("urllib.request.urlretrieve") as mock_retrieve:
                mock_retrieve.side_effect = (
                    lambda url, path, reporthook=None: Path(path).write_bytes(
                        tar_path.read_bytes()
                    )
                )

                dest_dir = tmp_path / "extracted"
                result = _download_and_extract(
                    "https://example.com/test.tar.gz", dest_dir
                )

                assert isinstance(result, list)
                assert len(result) == 2

    def test_creates_destination_directory(self, tmp_path: Path):
        """Test that _download_and_extract creates destination directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tar_path = Path(tmpdir) / "test.tar.gz"
            with tarfile.open(tar_path, "w:gz") as tf:
                test_file = Path(tmpdir) / "test.txt"
                test_file.write_text("test content")
                tf.add(test_file, arcname="llama.cpp-v1.2.3/README.md")

            with patch("urllib.request.urlretrieve") as mock_retrieve:
                mock_retrieve.side_effect = (
                    lambda url, path, reporthook=None: Path(path).write_bytes(
                        tar_path.read_bytes()
                    )
                )

                dest_dir = tmp_path / "new" / "directory"
                result = _download_and_extract(
                    "https://example.com/test.tar.gz", dest_dir
                )

                assert dest_dir.exists()

    def test_handles_empty_tar_gz(self, tmp_path: Path):
        """Test that _download_and_extract handles empty tar.gz."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tar_path = Path(tmpdir) / "empty.tar.gz"
            with tarfile.open(tar_path, "w:gz") as tf:
                pass  # Empty tar.gz

            with patch("urllib.request.urlretrieve") as mock_retrieve:
                mock_retrieve.side_effect = (
                    lambda url, path, reporthook=None: Path(path).write_bytes(
                        tar_path.read_bytes()
                    )
                )

                dest_dir = tmp_path / "extracted"
                result = _download_and_extract(
                    "https://example.com/empty.tar.gz", dest_dir
                )

                assert result == []

    def test_raises_url_error_on_network_failure(self, tmp_path: Path):
        """Test that _download_and_extract raises URLError on network failure."""
        with patch("urllib.request.urlretrieve") as mock_retrieve:
            mock_retrieve.side_effect = urllib.error.URLError("Network error")

            with pytest.raises(urllib.error.URLError):
                _download_and_extract(
                    "https://example.com/test.tar.gz", tmp_path / "extracted"
                )
