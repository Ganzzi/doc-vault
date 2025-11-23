"""
DocVault SDK - Scalable document management for organizations and AI agents.

This package provides a complete SDK for document upload, management,
version control, and access control across multiple organizations.
"""

from .config import Config
from .core import DocVaultSDK
from .database.schemas import (
    Agent,
    Document,
    DocumentACL,
    DocumentVersion,
    Organization,
)
from .exceptions import (
    AccessControlError,
    AgentNotFoundError,
    BucketError,
    ConfigurationError,
    ConnectionError,
    DatabaseError,
    DocumentDeletedError,
    DocumentError,
    DocumentNotFoundError,
    DocVaultError,
    DownloadError,
    InitializationError,
    IntegrityError,
    InvalidVersionError,
    OrganizationNotFoundError,
    PermissionDeniedError,
    QueryError,
    ServiceError,
    StorageConnectionError,
    StorageError,
    TransactionError,
    UploadError,
    ValidationError,
    VersionError,
    VersionNotFoundError,
)

__version__ = "2.2.1"
__all__ = [
    # Main classes
    "DocVaultSDK",
    "Config",
    # Schema classes
    "Organization",
    "Agent",
    "Document",
    "DocumentVersion",
    "DocumentACL",
    # Exceptions
    "DocVaultError",
    "ConfigurationError",
    "ValidationError",
    "DatabaseError",
    "ConnectionError",
    "QueryError",
    "IntegrityError",
    "StorageError",
    "UploadError",
    "DownloadError",
    "StorageConnectionError",
    "BucketError",
    "AccessControlError",
    "PermissionDeniedError",
    "OrganizationNotFoundError",
    "AgentNotFoundError",
    "DocumentError",
    "DocumentNotFoundError",
    "DocumentDeletedError",
    "VersionError",
    "VersionNotFoundError",
    "InvalidVersionError",
    "ServiceError",
    "TransactionError",
    "InitializationError",
]
