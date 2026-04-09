"""
Custom exceptions for the DocVault SDK.

This module defines the exception hierarchy used throughout the DocVault SDK.
All exceptions inherit from DocVaultError as the base exception.
"""

from typing import Any, Optional


class DocVaultError(Exception):
    """Base exception for all DocVault SDK errors."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(DocVaultError):
    """Raised when there are configuration-related errors."""

    pass


class ValidationError(DocVaultError):
    """Raised when input validation fails."""

    pass


class DatabaseError(DocVaultError):
    """Base class for database-related errors."""

    pass


class ConnectionError(DatabaseError):
    """Raised when database connection fails."""

    pass


class QueryError(DatabaseError):
    """Raised when a database query fails."""

    pass


class IntegrityError(DatabaseError):
    """Raised when database integrity constraints are violated."""

    pass


class StorageError(DocVaultError):
    """Base class for storage-related errors."""

    pass


class UploadError(StorageError):
    """Raised when file upload to storage fails."""

    pass


class DownloadError(StorageError):
    """Raised when file download from storage fails."""

    pass


class StorageConnectionError(StorageError):
    """Raised when storage service connection fails."""

    pass


class BucketError(StorageError):
    """Raised when bucket operations fail."""

    pass


class AccessControlError(DocVaultError):
    """Base class for access control and permission errors."""

    pass


class PermissionDeniedError(AccessControlError):
    """Raised when an operation is not permitted for the current agent."""

    pass


class OrganizationNotFoundError(AccessControlError):
    """Raised when an organization is not found."""

    pass


class AgentNotFoundError(AccessControlError):
    """Raised when an agent is not found."""

    pass


class DocumentError(DocVaultError):
    """Base class for document-related errors."""

    pass


class DocumentNotFoundError(DocumentError):
    """Raised when a document is not found."""

    pass


class DocumentDeletedError(DocumentError):
    """Raised when attempting to access a deleted document."""

    pass


class VersionError(DocumentError):
    """Base class for version-related errors."""

    pass


class VersionNotFoundError(VersionError):
    """Raised when a document version is not found."""

    pass


class InvalidVersionError(VersionError):
    """Raised when an invalid version number is provided."""

    pass


class ServiceError(DocVaultError):
    """Base class for service layer errors."""

    pass


class TransactionError(ServiceError):
    """Raised when a database transaction fails."""

    pass


class InitializationError(DocVaultError):
    """Raised when SDK initialization fails."""

    pass
