"""Local filesystem storage client for Chainlit elements.

This provides a local alternative to cloud storage providers (S3, Azure, GCS)
for development and self-hosted deployments.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Union

import aiofiles
from chainlit.data.storage_clients.base import BaseStorageClient

logger = logging.getLogger(__name__)


class LocalStorageClient(BaseStorageClient):
    """Local filesystem storage for Chainlit elements.

    Stores files in a local directory instead of cloud storage.
    Useful for development, testing, and self-hosted deployments.

    Args:
        storage_path: Path to directory for storing files (default: ".files/storage")
        base_url: Base URL for serving files (default: "file://")

    Example:
        >>> client = LocalStorageClient(storage_path=".files/storage")
        >>> await client.upload_file("image.png", b"...", mime="image/png")
        {'object_key': 'image.png', 'url': 'file://.../.files/storage/image.png'}

    Can be used as an async context manager:

        async with LocalStorageClient(".files/storage") as client:
            await client.upload_file("test.txt", b"data")
    """

    def __init__(self, storage_path: Union[str, Path], base_url: str = "file://"):
        """Initialize local storage client.

        Args:
            storage_path: Directory path for storing files (str or Path)
            base_url: Base URL for file access (use "file://" for local,
                     or "http://localhost:8000/files/" if serving via HTTP)
        """
        self.storage_path = Path(storage_path).resolve()
        self.base_url = base_url.rstrip("/")

        # Create storage directory if it doesn't exist
        self.storage_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"LocalStorageClient initialized: storage_path={self.storage_path}")

    def _validate_object_key(self, object_key: str) -> Path:
        """Validate object_key and return safe absolute path.

        Args:
            object_key: Unique identifier for the file (can include subdirectories)

        Returns:
            Resolved absolute path within storage_path

        Raises:
            ValueError: If object_key contains path traversal attempts
        """
        # Reject absolute paths and path traversal patterns
        if object_key.startswith("/"):
            raise ValueError(
                f"Invalid object_key: absolute paths not allowed: {object_key}"
            )
        if ".." in object_key:
            raise ValueError(
                f"Invalid object_key: path traversal detected: {object_key}"
            )

        # Resolve the path and verify it's within storage_path
        file_path = (self.storage_path / object_key).resolve()

        if not str(file_path).startswith(str(self.storage_path)):
            raise ValueError(
                f"Invalid object_key: escapes storage directory: {object_key}"
            )

        return file_path

    async def __aenter__(self) -> "LocalStorageClient":
        """Enter async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context manager."""
        await self.close()

    async def upload_file(
        self,
        object_key: str,
        data: Union[bytes, str],
        mime: str = "application/octet-stream",
        overwrite: bool = True,
        content_disposition: str | None = None,
    ) -> Dict[str, Any]:
        """Upload a file to local storage.

        Args:
            object_key: Unique identifier for the file (can include subdirectories)
            data: File content as bytes or string
            mime: MIME type of the file
            overwrite: Whether to overwrite existing file
            content_disposition: Ignored (for API compatibility with BaseStorageClient)

        Returns:
            Dict with object_key and url

        Raises:
            ValueError: If object_key is invalid (path traversal)
            FileExistsError: If file exists and overwrite=False
            IOError: If file write fails
        """
        file_path = self._validate_object_key(object_key)

        # Check if file exists and overwrite is False
        if file_path.exists() and not overwrite:
            raise FileExistsError(
                f"File already exists: {object_key} (overwrite=False)"
            )

        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        if isinstance(data, bytes):
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(data)
        else:
            async with aiofiles.open(file_path, "w") as f:
                await f.write(str(data))

        # Generate URL
        url = f"{self.base_url}/{file_path.absolute()}"

        logger.debug(f"Uploaded file: {object_key} ({mime})")

        return {"object_key": object_key, "url": url}

    async def delete_file(self, object_key: str) -> bool:
        """Delete a file from local storage.

        Args:
            object_key: Unique identifier for the file

        Returns:
            True if file was deleted, False if file didn't exist

        Raises:
            ValueError: If object_key is invalid (path traversal)
        """
        file_path = self._validate_object_key(object_key)

        if file_path.exists() and file_path.is_file():
            file_path.unlink()
            logger.debug(f"Deleted file: {object_key}")
            return True

        logger.warning(f"File not found for deletion: {object_key}")
        return False

    async def get_read_url(self, object_key: str) -> str:
        """Get a URL for reading a file.

        Args:
            object_key: Unique identifier for the file

        Returns:
            URL to access the file, or the object_key if file not found
            (for compatibility with base class signature)

        Raises:
            ValueError: If object_key is invalid (path traversal)
        """
        file_path = self._validate_object_key(object_key)

        if not file_path.exists():
            logger.warning(f"File not found: {object_key}")
            return object_key

        url = f"{self.base_url}/{file_path.absolute()}"
        return url

    async def close(self) -> None:
        """Close the storage client.

        For local storage, there are no connections to close.
        """
        logger.debug("LocalStorageClient closed")
