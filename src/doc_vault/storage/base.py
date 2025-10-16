"""
Abstract storage backend interface for DocVault.

This module defines the abstract base class for storage backends,
providing a consistent interface for different storage implementations
like S3/MinIO, local filesystem, etc.
"""

from abc import ABC, abstractmethod
from typing import Protocol


class StorageBackend(ABC):
    """
    Abstract base class for storage backends.

    This interface defines the contract that all storage backends must implement,
    providing a consistent API for uploading, downloading, and managing files
    across different storage systems (S3/MinIO, local filesystem, etc.).
    """

    @abstractmethod
    async def upload(
        self, bucket: str, path: str, data: bytes, content_type: str
    ) -> str:
        """
        Upload file data to storage.

        Args:
            bucket: The bucket/container name
            path: The object path within the bucket
            data: The file data as bytes
            content_type: MIME type of the file

        Returns:
            The storage URL/path of the uploaded file

        Raises:
            StorageError: If upload fails
        """
        pass

    @abstractmethod
    async def download(self, bucket: str, path: str) -> bytes:
        """
        Download file data from storage.

        Args:
            bucket: The bucket/container name
            path: The object path within the bucket

        Returns:
            The file data as bytes

        Raises:
            StorageError: If download fails or file doesn't exist
        """
        pass

    @abstractmethod
    async def delete(self, bucket: str, path: str) -> None:
        """
        Delete a file from storage.

        Args:
            bucket: The bucket/container name
            path: The object path within the bucket

        Raises:
            StorageError: If deletion fails
        """
        pass

    @abstractmethod
    async def exists(self, bucket: str, path: str) -> bool:
        """
        Check if a file exists in storage.

        Args:
            bucket: The bucket/container name
            path: The object path within the bucket

        Returns:
            True if the file exists, False otherwise
        """
        pass

    @abstractmethod
    async def create_bucket(self, bucket: str) -> None:
        """
        Create a bucket/container if it doesn't exist.

        Args:
            bucket: The bucket/container name to create

        Raises:
            StorageError: If bucket creation fails
        """
        pass

    @abstractmethod
    async def generate_presigned_url(
        self, bucket: str, path: str, expiry: int = 3600
    ) -> str:
        """
        Generate a presigned URL for temporary access to a file.

        Args:
            bucket: The bucket/container name
            path: The object path within the bucket
            expiry: URL expiry time in seconds (default: 1 hour)

        Returns:
            A presigned URL that can be used to access the file

        Raises:
            StorageError: If URL generation fails
        """
        pass


class StorageError(Exception):
    """Base exception for storage-related errors."""

    def __init__(self, message: str, bucket: str = None, path: str = None):
        self.bucket = bucket
        self.path = path
        super().__init__(message)


class BucketNotFoundError(StorageError):
    """Raised when a bucket doesn't exist."""

    def __init__(self, bucket: str):
        super().__init__(f"Bucket '{bucket}' not found", bucket=bucket)


class ObjectNotFoundError(StorageError):
    """Raised when an object doesn't exist."""

    def __init__(self, bucket: str, path: str):
        super().__init__(
            f"Object '{path}' not found in bucket '{bucket}'", bucket=bucket, path=path
        )


class UploadError(StorageError):
    """Raised when file upload fails."""

    def __init__(self, bucket: str, path: str, original_error: Exception = None):
        message = f"Failed to upload '{path}' to bucket '{bucket}'"
        if original_error:
            message += f": {original_error}"
        super().__init__(message, bucket=bucket, path=path)


class DownloadError(StorageError):
    """Raised when file download fails."""

    def __init__(self, bucket: str, path: str, original_error: Exception = None):
        message = f"Failed to download '{path}' from bucket '{bucket}'"
        if original_error:
            message += f": {original_error}"
        super().__init__(message, bucket=bucket, path=path)


class DeleteError(StorageError):
    """Raised when file deletion fails."""

    def __init__(self, bucket: str, path: str, original_error: Exception = None):
        message = f"Failed to delete '{path}' from bucket '{bucket}'"
        if original_error:
            message += f": {original_error}"
        super().__init__(message, bucket=bucket, path=path)
