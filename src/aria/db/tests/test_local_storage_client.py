"""Tests for LocalStorageClient."""

from pathlib import Path

import pytest

from aria.db.local_storage_client import LocalStorageClient


class TestLocalStorageClient:
    """Test suite for LocalStorageClient."""

    @pytest.mark.asyncio
    async def test_initialization(self, tmp_path: Path):
        """Test LocalStorageClient initialization."""
        storage_path = tmp_path / "storage"
        client = LocalStorageClient(storage_path=str(storage_path))

        assert client.storage_path == storage_path
        assert storage_path.exists()
        assert storage_path.is_dir()

    @pytest.mark.asyncio
    async def test_upload_file_bytes(self, tmp_path: Path):
        """Test uploading a file with bytes data."""
        client = LocalStorageClient(storage_path=str(tmp_path / "storage"))

        data = b"Hello, World!"
        result = await client.upload_file(
            object_key="test.txt", data=data, mime="text/plain"
        )

        assert result["object_key"] == "test.txt"
        assert "url" in result

        # Verify file was created
        file_path = client.storage_path / "test.txt"
        assert file_path.exists()
        assert file_path.read_bytes() == data

    @pytest.mark.asyncio
    async def test_upload_file_string(self, tmp_path: Path):
        """Test uploading a file with string data."""
        client = LocalStorageClient(storage_path=str(tmp_path / "storage"))

        data = "Hello, World!"
        result = await client.upload_file(
            object_key="test.txt", data=data, mime="text/plain"
        )

        assert result["object_key"] == "test.txt"

        # Verify file was created
        file_path = client.storage_path / "test.txt"
        assert file_path.exists()
        assert file_path.read_text() == data

    @pytest.mark.asyncio
    async def test_upload_file_with_subdirectory(self, tmp_path: Path):
        """Test uploading a file with subdirectory in object_key."""
        client = LocalStorageClient(storage_path=str(tmp_path / "storage"))

        data = b"Test data"
        result = await client.upload_file(
            object_key="subdir/nested/file.bin", data=data
        )

        assert result["object_key"] == "subdir/nested/file.bin"

        # Verify file and directories were created
        file_path = client.storage_path / "subdir" / "nested" / "file.bin"
        assert file_path.exists()
        assert file_path.read_bytes() == data

    @pytest.mark.asyncio
    async def test_upload_file_overwrite_true(self, tmp_path: Path):
        """Test uploading a file with overwrite=True."""
        client = LocalStorageClient(storage_path=str(tmp_path / "storage"))

        # Upload first file
        await client.upload_file(
            object_key="test.txt", data=b"Original", overwrite=True
        )

        # Upload again with overwrite=True
        result = await client.upload_file(
            object_key="test.txt", data=b"Updated", overwrite=True
        )

        assert result["object_key"] == "test.txt"

        # Verify file was overwritten
        file_path = client.storage_path / "test.txt"
        assert file_path.read_bytes() == b"Updated"

    @pytest.mark.asyncio
    async def test_upload_file_overwrite_false(self, tmp_path: Path):
        """Test uploading a file with overwrite=False raises error."""
        client = LocalStorageClient(storage_path=str(tmp_path / "storage"))

        # Upload first file
        await client.upload_file(
            object_key="test.txt", data=b"Original", overwrite=True
        )

        # Try to upload again with overwrite=False
        result = await client.upload_file(
            object_key="test.txt", data=b"Updated", overwrite=False
        )

        # Should return empty dict on error
        assert result == {}

        # Verify original file was not overwritten
        file_path = client.storage_path / "test.txt"
        assert file_path.read_bytes() == b"Original"

    @pytest.mark.asyncio
    async def test_delete_file_exists(self, tmp_path: Path):
        """Test deleting an existing file."""
        client = LocalStorageClient(storage_path=str(tmp_path / "storage"))

        # Create a file
        await client.upload_file(object_key="test.txt", data=b"Test")

        # Delete the file
        result = await client.delete_file("test.txt")

        assert result is True

        # Verify file was deleted
        file_path = client.storage_path / "test.txt"
        assert not file_path.exists()

    @pytest.mark.asyncio
    async def test_delete_file_not_exists(self, tmp_path: Path):
        """Test deleting a non-existent file."""
        client = LocalStorageClient(storage_path=str(tmp_path / "storage"))

        result = await client.delete_file("nonexistent.txt")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_read_url_exists(self, tmp_path: Path):
        """Test getting read URL for existing file."""
        client = LocalStorageClient(storage_path=str(tmp_path / "storage"))

        # Create a file
        await client.upload_file(object_key="test.txt", data=b"Test")

        # Get read URL
        url = await client.get_read_url("test.txt")

        assert "test.txt" in url
        assert url.startswith("file://")

    @pytest.mark.asyncio
    async def test_get_read_url_not_exists(self, tmp_path: Path):
        """Test getting read URL for non-existent file."""
        client = LocalStorageClient(storage_path=str(tmp_path / "storage"))

        url = await client.get_read_url("nonexistent.txt")

        # Should return the object_key as fallback
        assert url == "nonexistent.txt"

    @pytest.mark.asyncio
    async def test_custom_base_url(self, tmp_path: Path):
        """Test LocalStorageClient with custom base URL."""
        client = LocalStorageClient(
            storage_path=str(tmp_path / "storage"),
            base_url="http://localhost:8000/files",
        )

        await client.upload_file(object_key="test.txt", data=b"Test")

        url = await client.get_read_url("test.txt")

        assert url.startswith("http://localhost:8000/files/")
        assert "test.txt" in url

    @pytest.mark.asyncio
    async def test_close(self, tmp_path: Path):
        """Test closing the storage client."""
        client = LocalStorageClient(storage_path=str(tmp_path / "storage"))

        # Should not raise any errors
        await client.close()

    @pytest.mark.asyncio
    async def test_upload_multiple_files(self, tmp_path: Path):
        """Test uploading multiple files."""
        client = LocalStorageClient(storage_path=str(tmp_path / "storage"))

        files = {
            "file1.txt": b"Content 1",
            "file2.txt": b"Content 2",
            "subdir/file3.txt": b"Content 3",
        }

        for object_key, data in files.items():
            result = await client.upload_file(object_key=object_key, data=data)
            assert result["object_key"] == object_key

        # Verify all files exist
        for object_key, data in files.items():
            file_path = client.storage_path / object_key
            assert file_path.exists()
            assert file_path.read_bytes() == data

    @pytest.mark.asyncio
    async def test_delete_multiple_files(self, tmp_path: Path):
        """Test deleting multiple files."""
        client = LocalStorageClient(storage_path=str(tmp_path / "storage"))

        # Create files
        files = ["file1.txt", "file2.txt", "file3.txt"]
        for object_key in files:
            await client.upload_file(object_key=object_key, data=b"Test")

        # Delete all files
        for object_key in files:
            result = await client.delete_file(object_key)
            assert result is True

        # Verify all files deleted
        for object_key in files:
            file_path = client.storage_path / object_key
            assert not file_path.exists()

    @pytest.mark.asyncio
    async def test_upload_binary_data(self, tmp_path: Path):
        """Test uploading binary data (e.g., image)."""
        client = LocalStorageClient(storage_path=str(tmp_path / "storage"))

        # Simulate binary image data
        binary_data = bytes(range(256))

        result = await client.upload_file(
            object_key="image.png", data=binary_data, mime="image/png"
        )

        assert result["object_key"] == "image.png"

        # Verify binary data preserved
        file_path = client.storage_path / "image.png"
        assert file_path.read_bytes() == binary_data

    @pytest.mark.asyncio
    async def test_upload_unicode_content(self, tmp_path: Path):
        """Test uploading file with unicode content."""
        client = LocalStorageClient(storage_path=str(tmp_path / "storage"))

        unicode_data = "Hello 世界 🌍 Привет"

        result = await client.upload_file(
            object_key="unicode.txt", data=unicode_data, mime="text/plain"
        )

        assert result["object_key"] == "unicode.txt"

        # Verify unicode preserved
        file_path = client.storage_path / "unicode.txt"
        assert file_path.read_text() == unicode_data
