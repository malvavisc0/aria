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
    """

    def __init__(self, storage_path: Union[str, Path], base_url: str = "file://"):
        """Initialize local storage client.

        Args:
            storage_path: Directory path for storing files (str or Path)
            base_url: Base URL for file access (use "file://" for local,
                     or "http://localhost:8000/files/" if serving via HTTP)
        """
        self.storage_path = Path(storage_path)
        self.base_url = base_url.rstrip("/")

        # Create storage directory if it doesn't exist
        self.storage_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"LocalStorageClient initialized: storage_path={self.storage_path}")

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
            content_disposition: Content disposition header (not used for local storage)

        Returns:
            Dict with object_key and url

        Raises:
            FileExistsError: If file exists and overwrite=False
        """
        try:
            file_path = self.storage_path / object_key

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

        except Exception as e:
            logger.warning(f"LocalStorageClient upload_file error: {e}")
            return {}

    async def delete_file(self, object_key: str) -> bool:
        """Delete a file from local storage.

        Args:
            object_key: Unique identifier for the file

        Returns:
            True if file was deleted, False otherwise
        """
        try:
            file_path = self.storage_path / object_key

            if file_path.exists() and file_path.is_file():
                file_path.unlink()
                logger.debug(f"Deleted file: {object_key}")
                return True

            logger.warning(f"File not found for deletion: {object_key}")
            return False

        except Exception as e:
            logger.warning(f"LocalStorageClient delete_file error: {e}")
            return False

    async def get_read_url(self, object_key: str) -> str:
        """Get a URL for reading a file.

        Args:
            object_key: Unique identifier for the file

        Returns:
            URL to access the file
        """
        try:
            file_path = self.storage_path / object_key

            if not file_path.exists():
                logger.warning(f"File not found: {object_key}")
                return object_key

            url = f"{self.base_url}/{file_path.absolute()}"
            return url

        except Exception as e:
            logger.warning(f"LocalStorageClient get_read_url error: {e}")
            return object_key

    async def close(self) -> None:
        """Close the storage client.

        For local storage, there are no connections to close.
        """
        logger.debug("LocalStorageClient closed")
        pass
