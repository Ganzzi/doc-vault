"""
S3/MinIO storage backend implementation for DocVault.

This module provides an S3-compatible storage backend using the MinIO Python client,
supporting both MinIO and AWS S3 as storage backends.
"""

import io
from typing import Optional
from urllib.parse import urljoin

from minio import Minio
from minio.error import S3Error

from .base import (
    BucketNotFoundError,
    DeleteError,
    DownloadError,
    ObjectNotFoundError,
    StorageBackend,
    StorageError,
    UploadError,
)


class S3StorageBackend(StorageBackend):
    """
    S3/MinIO storage backend implementation.

    This backend uses the MinIO Python client to interact with S3-compatible storage
    systems including MinIO, AWS S3, and other S3-compatible services.
    """

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        secure: bool = False,
        region: Optional[str] = None,
    ):
        """
        Initialize the S3 storage backend.

        Args:
            endpoint: S3 endpoint URL (e.g., 'localhost:9000' for MinIO)
            access_key: S3 access key
            secret_key: S3 secret key
            secure: Whether to use HTTPS (default: False for local MinIO)
            region: AWS region (optional, mainly for AWS S3)
        """
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.secure = secure
        self.region = region

        # Initialize MinIO client
        self.client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
            region=region,
        )

    async def upload(
        self, bucket: str, path: str, data: bytes, content_type: str
    ) -> str:
        """
        Upload file data to S3/MinIO storage.

        Args:
            bucket: The bucket/container name
            path: The object path within the bucket
            data: The file data as bytes
            content_type: MIME type of the file

        Returns:
            The storage URL/path of the uploaded file

        Raises:
            UploadError: If upload fails
            BucketNotFoundError: If bucket doesn't exist
        """
        try:
            # Convert bytes to file-like object for MinIO
            data_stream = io.BytesIO(data)
            data_length = len(data)

            # Upload the object
            self.client.put_object(
                bucket_name=bucket,
                object_name=path,
                data=data_stream,
                length=data_length,
                content_type=content_type,
            )

            # Return the storage path (could be extended to return full URL)
            return f"s3://{bucket}/{path}"

        except S3Error as e:
            if e.code == "NoSuchBucket":
                raise BucketNotFoundError(bucket) from e
            elif e.code == "AccessDenied":
                raise UploadError(bucket, path, e) from e
            else:
                raise UploadError(bucket, path, e) from e
        except Exception as e:
            raise UploadError(bucket, path, e) from e

    async def download(self, bucket: str, path: str) -> bytes:
        """
        Download file data from S3/MinIO storage.

        Args:
            bucket: The bucket/container name
            path: The object path within the bucket

        Returns:
            The file data as bytes

        Raises:
            DownloadError: If download fails
            BucketNotFoundError: If bucket doesn't exist
            ObjectNotFoundError: If object doesn't exist
        """
        try:
            # Get the object
            response = self.client.get_object(bucket_name=bucket, object_name=path)

            # Read all data from the response
            data = response.read()

            # Close the response
            response.close()
            response.release_conn()

            return data

        except S3Error as e:
            if e.code == "NoSuchBucket":
                raise BucketNotFoundError(bucket) from e
            elif e.code == "NoSuchKey":
                raise ObjectNotFoundError(bucket, path) from e
            elif e.code == "AccessDenied":
                raise DownloadError(bucket, path, e) from e
            else:
                raise DownloadError(bucket, path, e) from e
        except Exception as e:
            raise DownloadError(bucket, path, e) from e

    async def delete(self, bucket: str, path: str) -> None:
        """
        Delete a file from S3/MinIO storage.

        Args:
            bucket: The bucket/container name
            path: The object path within the bucket

        Raises:
            DeleteError: If deletion fails
            BucketNotFoundError: If bucket doesn't exist
        """
        try:
            # Delete the object
            self.client.remove_object(bucket_name=bucket, object_name=path)

        except S3Error as e:
            if e.code == "NoSuchBucket":
                raise BucketNotFoundError(bucket) from e
            elif e.code == "NoSuchKey":
                # Object doesn't exist - this is not necessarily an error
                # for delete operations (idempotent)
                pass
            elif e.code == "AccessDenied":
                raise DeleteError(bucket, path, e) from e
            else:
                raise DeleteError(bucket, path, e) from e
        except Exception as e:
            raise DeleteError(bucket, path, e) from e

    async def exists(self, bucket: str, path: str) -> bool:
        """
        Check if a file exists in S3/MinIO storage.

        Args:
            bucket: The bucket/container name
            path: The object path within the bucket

        Returns:
            True if the file exists, False otherwise

        Raises:
            BucketNotFoundError: If bucket doesn't exist
        """
        try:
            # Try to get object stats - this is more efficient than downloading
            self.client.stat_object(bucket_name=bucket, object_name=path)
            return True

        except S3Error as e:
            if e.code == "NoSuchBucket":
                raise BucketNotFoundError(bucket) from e
            elif e.code == "NoSuchKey":
                return False
            else:
                # For other errors, assume the object doesn't exist
                return False
        except Exception:
            # For any other errors, assume the object doesn't exist
            return False

    async def create_bucket(self, bucket: str) -> None:
        """
        Create a bucket/container if it doesn't exist.

        Args:
            bucket: The bucket/container name to create

        Raises:
            StorageError: If bucket creation fails
        """
        try:
            # Check if bucket already exists
            if not self.client.bucket_exists(bucket_name=bucket):
                # Create the bucket
                self.client.make_bucket(bucket_name=bucket)

        except S3Error as e:
            if e.code == "BucketAlreadyExists":
                # Bucket already exists - this is not an error
                pass
            elif e.code == "AccessDenied":
                raise StorageError(
                    f"Access denied creating bucket '{bucket}'", bucket=bucket
                ) from e
            else:
                raise StorageError(
                    f"Failed to create bucket '{bucket}': {e}", bucket=bucket
                ) from e
        except Exception as e:
            raise StorageError(
                f"Failed to create bucket '{bucket}': {e}", bucket=bucket
            ) from e

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
            BucketNotFoundError: If bucket doesn't exist
            ObjectNotFoundError: If object doesn't exist
        """
        try:
            # Generate presigned URL for GET operation
            url = self.client.presigned_get_object(
                bucket_name=bucket,
                object_name=path,
                expires=expiry,
            )
            return url

        except S3Error as e:
            if e.code == "NoSuchBucket":
                raise BucketNotFoundError(bucket) from e
            elif e.code == "NoSuchKey":
                raise ObjectNotFoundError(bucket, path) from e
            elif e.code == "AccessDenied":
                raise StorageError(
                    f"Access denied generating URL for '{path}' in bucket '{bucket}'",
                    bucket=bucket,
                    path=path,
                ) from e
            else:
                raise StorageError(
                    f"Failed to generate presigned URL for '{path}' in bucket '{bucket}': {e}",
                    bucket=bucket,
                    path=path,
                ) from e
        except Exception as e:
            raise StorageError(
                f"Failed to generate presigned URL for '{path}' in bucket '{bucket}': {e}",
                bucket=bucket,
                path=path,
            ) from e
