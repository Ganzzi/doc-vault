"""
Unit tests for the storage layer.

This module contains comprehensive tests for the storage backends,
focusing on the S3StorageBackend implementation with mocked MinIO client.
"""

import io
import pytest
from unittest.mock import MagicMock, patch, Mock

from doc_vault.storage.base import (
    BucketNotFoundError,
    ObjectNotFoundError,
    UploadError,
    DownloadError,
    DeleteError,
    StorageError,
)
from doc_vault.storage.s3_client import S3StorageBackend


class TestS3StorageBackend:
    """Test suite for S3StorageBackend."""

    @pytest.fixture
    def mock_minio_client(self):
        """Create a mocked MinIO client."""
        client = MagicMock()
        return client

    @pytest.fixture
    def storage_backend(self, mock_minio_client):
        """Create S3StorageBackend instance with mocked client."""
        with patch("doc_vault.storage.s3_client.Minio", return_value=mock_minio_client):
            backend = S3StorageBackend(
                endpoint="localhost:9000",
                access_key="test_key",
                secret_key="test_secret",
                secure=False,
            )
            backend.client = mock_minio_client
            return backend

    @pytest.mark.asyncio
    async def test_upload_success(self, storage_backend, mock_minio_client):
        """Test successful file upload."""
        # Arrange
        bucket = "test-bucket"
        path = "test/file.txt"
        data = b"Hello, World!"
        content_type = "text/plain"

        # Act
        result = await storage_backend.upload(bucket, path, data, content_type)

        # Assert
        mock_minio_client.put_object.assert_called_once()
        call_args = mock_minio_client.put_object.call_args
        assert call_args.kwargs["bucket_name"] == bucket
        assert call_args.kwargs["object_name"] == path
        assert call_args.kwargs["length"] == len(data)
        assert call_args.kwargs["content_type"] == content_type
        # Check that data is a BytesIO object with correct content
        assert isinstance(call_args.kwargs["data"], io.BytesIO)
        call_args.kwargs["data"].seek(0)
        assert call_args.kwargs["data"].read() == data
        assert result == f"s3://{bucket}/{path}"

    @pytest.mark.asyncio
    async def test_upload_bucket_not_found(self, storage_backend, mock_minio_client):
        """Test upload failure when bucket doesn't exist."""
        # Arrange
        bucket = "nonexistent-bucket"
        path = "test/file.txt"
        data = b"Hello, World!"
        content_type = "text/plain"

        from minio.error import S3Error

        mock_minio_client.put_object.side_effect = S3Error(
            code="NoSuchBucket",
            message="Bucket does not exist",
            resource="test",
            request_id="123",
            host_id="456",
            response=MagicMock(),
        )

        # Act & Assert
        with pytest.raises(BucketNotFoundError) as exc_info:
            await storage_backend.upload(bucket, path, data, content_type)

        assert exc_info.value.bucket == bucket
        assert exc_info.value.path is None  # BucketNotFoundError doesn't set path

    @pytest.mark.asyncio
    async def test_upload_access_denied(self, storage_backend, mock_minio_client):
        """Test upload failure when access is denied."""
        # Arrange
        bucket = "test-bucket"
        path = "test/file.txt"
        data = b"Hello, World!"
        content_type = "text/plain"

        from minio.error import S3Error

        mock_minio_client.put_object.side_effect = S3Error(
            code="AccessDenied",
            message="Access denied",
            resource="test",
            request_id="123",
            host_id="456",
            response=MagicMock(),
        )

        # Act & Assert
        with pytest.raises(UploadError) as exc_info:
            await storage_backend.upload(bucket, path, data, content_type)

        assert exc_info.value.bucket == bucket
        assert exc_info.value.path == path

    @pytest.mark.asyncio
    async def test_download_success(self, storage_backend, mock_minio_client):
        """Test successful file download."""
        # Arrange
        bucket = "test-bucket"
        path = "test/file.txt"
        expected_data = b"Hello, World!"

        # Mock the response object
        mock_response = MagicMock()
        mock_response.read.return_value = expected_data
        mock_minio_client.get_object.return_value = mock_response

        # Act
        result = await storage_backend.download(bucket, path)

        # Assert
        mock_minio_client.get_object.assert_called_once_with(
            bucket_name=bucket,
            object_name=path,
        )
        mock_response.read.assert_called_once()
        mock_response.close.assert_called_once()
        mock_response.release_conn.assert_called_once()
        assert result == expected_data

    @pytest.mark.asyncio
    async def test_download_object_not_found(self, storage_backend, mock_minio_client):
        """Test download failure when object doesn't exist."""
        # Arrange
        bucket = "test-bucket"
        path = "nonexistent/file.txt"

        from minio.error import S3Error

        mock_minio_client.get_object.side_effect = S3Error(
            code="NoSuchKey",
            message="Object does not exist",
            resource="test",
            request_id="123",
            host_id="456",
            response=MagicMock(),
        )

        # Act & Assert
        with pytest.raises(ObjectNotFoundError) as exc_info:
            await storage_backend.download(bucket, path)

        assert exc_info.value.bucket == bucket
        assert exc_info.value.path == path

    @pytest.mark.asyncio
    async def test_download_bucket_not_found(self, storage_backend, mock_minio_client):
        """Test download failure when bucket doesn't exist."""
        # Arrange
        bucket = "nonexistent-bucket"
        path = "test/file.txt"

        from minio.error import S3Error

        mock_minio_client.get_object.side_effect = S3Error(
            code="NoSuchBucket",
            message="Bucket does not exist",
            resource="test",
            request_id="123",
            host_id="456",
            response=MagicMock(),
        )

        # Act & Assert
        with pytest.raises(BucketNotFoundError) as exc_info:
            await storage_backend.download(bucket, path)

        assert exc_info.value.bucket == bucket

    @pytest.mark.asyncio
    async def test_delete_success(self, storage_backend, mock_minio_client):
        """Test successful file deletion."""
        # Arrange
        bucket = "test-bucket"
        path = "test/file.txt"

        # Act
        await storage_backend.delete(bucket, path)

        # Assert
        mock_minio_client.remove_object.assert_called_once_with(
            bucket_name=bucket,
            object_name=path,
        )

    @pytest.mark.asyncio
    async def test_delete_object_not_found(self, storage_backend, mock_minio_client):
        """Test delete when object doesn't exist (should not raise error)."""
        # Arrange
        bucket = "test-bucket"
        path = "nonexistent/file.txt"

        from minio.error import S3Error

        mock_minio_client.remove_object.side_effect = S3Error(
            code="NoSuchKey",
            message="Object does not exist",
            resource="test",
            request_id="123",
            host_id="456",
            response=MagicMock(),
        )

        # Act & Assert - should not raise
        await storage_backend.delete(bucket, path)
        mock_minio_client.remove_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_exists_object_exists(self, storage_backend, mock_minio_client):
        """Test exists check when object exists."""
        # Arrange
        bucket = "test-bucket"
        path = "test/file.txt"

        # Act
        result = await storage_backend.exists(bucket, path)

        # Assert
        mock_minio_client.stat_object.assert_called_once_with(
            bucket_name=bucket,
            object_name=path,
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_object_not_found(self, storage_backend, mock_minio_client):
        """Test exists check when object doesn't exist."""
        # Arrange
        bucket = "test-bucket"
        path = "nonexistent/file.txt"

        from minio.error import S3Error

        mock_minio_client.stat_object.side_effect = S3Error(
            code="NoSuchKey",
            message="Object does not exist",
            resource="test",
            request_id="123",
            host_id="456",
            response=MagicMock(),
        )

        # Act
        result = await storage_backend.exists(bucket, path)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_exists_bucket_not_found(self, storage_backend, mock_minio_client):
        """Test exists check when bucket doesn't exist."""
        # Arrange
        bucket = "nonexistent-bucket"
        path = "test/file.txt"

        from minio.error import S3Error

        mock_minio_client.stat_object.side_effect = S3Error(
            code="NoSuchBucket",
            message="Bucket does not exist",
            resource="test",
            request_id="123",
            host_id="456",
            response=MagicMock(),
        )

        # Act & Assert
        with pytest.raises(BucketNotFoundError) as exc_info:
            await storage_backend.exists(bucket, path)

        assert exc_info.value.bucket == bucket

    @pytest.mark.asyncio
    async def test_create_bucket_new_bucket(self, storage_backend, mock_minio_client):
        """Test creating a new bucket."""
        # Arrange
        bucket = "new-bucket"
        mock_minio_client.bucket_exists.return_value = False

        # Act
        await storage_backend.create_bucket(bucket)

        # Assert
        mock_minio_client.bucket_exists.assert_called_once_with(bucket_name=bucket)
        mock_minio_client.make_bucket.assert_called_once_with(bucket_name=bucket)

    @pytest.mark.asyncio
    async def test_create_bucket_already_exists(
        self, storage_backend, mock_minio_client
    ):
        """Test creating a bucket that already exists."""
        # Arrange
        bucket = "existing-bucket"
        mock_minio_client.bucket_exists.return_value = True

        # Act
        await storage_backend.create_bucket(bucket)

        # Assert
        mock_minio_client.bucket_exists.assert_called_once_with(bucket_name=bucket)
        mock_minio_client.make_bucket.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_bucket_access_denied(
        self, storage_backend, mock_minio_client
    ):
        """Test bucket creation failure due to access denied."""
        # Arrange
        bucket = "test-bucket"
        mock_minio_client.bucket_exists.return_value = False

        from minio.error import S3Error

        mock_minio_client.make_bucket.side_effect = S3Error(
            code="AccessDenied",
            message="Access denied",
            resource="test",
            request_id="123",
            host_id="456",
            response=MagicMock(),
        )

        # Act & Assert
        with pytest.raises(StorageError) as exc_info:
            await storage_backend.create_bucket(bucket)

        assert exc_info.value.bucket == bucket

    @pytest.mark.asyncio
    async def test_generate_presigned_url_success(
        self, storage_backend, mock_minio_client
    ):
        """Test successful presigned URL generation."""
        # Arrange
        bucket = "test-bucket"
        path = "test/file.txt"
        expiry = 3600
        expected_url = "https://example.com/presigned-url"

        mock_minio_client.presigned_get_object.return_value = expected_url

        # Act
        result = await storage_backend.generate_presigned_url(bucket, path, expiry)

        # Assert
        mock_minio_client.presigned_get_object.assert_called_once_with(
            bucket_name=bucket,
            object_name=path,
            expires=expiry,
        )
        assert result == expected_url

    @pytest.mark.asyncio
    async def test_generate_presigned_url_object_not_found(
        self, storage_backend, mock_minio_client
    ):
        """Test presigned URL generation when object doesn't exist."""
        # Arrange
        bucket = "test-bucket"
        path = "nonexistent/file.txt"
        expiry = 3600

        from minio.error import S3Error

        mock_minio_client.presigned_get_object.side_effect = S3Error(
            code="NoSuchKey",
            message="Object does not exist",
            resource="test",
            request_id="123",
            host_id="456",
            response=MagicMock(),
        )

        # Act & Assert
        with pytest.raises(ObjectNotFoundError) as exc_info:
            await storage_backend.generate_presigned_url(bucket, path, expiry)

        assert exc_info.value.bucket == bucket
        assert exc_info.value.path == path

    def test_initialization(self):
        """Test S3StorageBackend initialization."""
        # Arrange & Act
        with patch("doc_vault.storage.s3_client.Minio") as mock_minio_class:
            backend = S3StorageBackend(
                endpoint="localhost:9000",
                access_key="test_key",
                secret_key="test_secret",
                secure=True,
                region="us-east-1",
            )

            # Assert
            mock_minio_class.assert_called_once_with(
                endpoint="localhost:9000",
                access_key="test_key",
                secret_key="test_secret",
                secure=True,
                region="us-east-1",
            )
            assert backend.endpoint == "localhost:9000"
            assert backend.access_key == "test_key"
            assert backend.secret_key == "test_secret"
            assert backend.secure is True
            assert backend.region == "us-east-1"
