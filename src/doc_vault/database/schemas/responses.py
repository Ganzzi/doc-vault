"""
Response models for DocVault SDK methods (v2.2).

These models define the structure of responses returned by public SDK methods.
They replace generic Dict[str, Any] return types with type-safe Pydantic models.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .acl import DocumentACL
from .document import Document
from .version import DocumentVersion


class PaginationMeta(BaseModel):
    """Pagination metadata for list and search responses."""

    model_config = ConfigDict(from_attributes=True)

    total: int = Field(..., description="Total number of items in the result set", ge=0)
    limit: int = Field(..., description="Maximum items per page", ge=1, le=1000)
    offset: int = Field(..., description="Starting offset in the result set", ge=0)
    has_more: bool = Field(
        ..., description="Whether more items exist beyond the current page"
    )


class DocumentListResponse(BaseModel):
    """Response model for list_docs() method.

    Provides paginated list of documents with filters and pagination metadata.
    """

    model_config = ConfigDict(from_attributes=True)

    documents: List[Document] = Field(
        default_factory=list,
        description="List of documents returned for the current page",
    )
    pagination: PaginationMeta = Field(
        ...,
        description="Pagination information including total count and has_more flag",
    )
    filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Filters that were applied to generate this result set",
    )


class SearchResponse(BaseModel):
    """Response model for search() method.

    Provides search results with query information and pagination.
    """

    model_config = ConfigDict(from_attributes=True)

    documents: List[Document] = Field(
        default_factory=list,
        description="Documents matching the search query",
    )
    query: str = Field(..., description="The search query that was executed")
    pagination: PaginationMeta = Field(
        ..., description="Pagination information for search results"
    )
    filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional filters that were applied to the search",
    )


class DocumentDetails(BaseModel):
    """Response model for get_document_details() method.

    Provides comprehensive document information with optional versions and permissions.
    Permissions are only included for ADMIN users and when explicitly requested.
    """

    model_config = ConfigDict(from_attributes=True)

    document: Document = Field(..., description="Core document metadata")
    versions: Optional[List[DocumentVersion]] = Field(
        None,
        description="Version history (included only if requested via include_versions=True)",
    )
    permissions: Optional[List[DocumentACL]] = Field(
        None,
        description="Access permissions (included only if ADMIN and include_permissions=True)",
    )
    version_count: int = Field(
        ..., description="Total number of versions for this document", ge=1
    )
    current_version: int = Field(..., description="Current/active version number", ge=1)


class PermissionListResponse(BaseModel):
    """Response model for get_permissions() method.

    Provides list of permissions on a document with metadata about the request.
    """

    model_config = ConfigDict(from_attributes=True)

    document_id: UUID = Field(
        ..., description="UUID of the document these permissions are for"
    )
    permissions: List[DocumentACL] = Field(
        default_factory=list,
        description="List of access permissions on the document",
    )
    total: int = Field(
        ..., description="Total count of permissions on the document", ge=0
    )
    requested_by: Optional[UUID] = Field(
        None,
        description="Agent ID who requested the permissions (if available)",
    )
    requested_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when permissions were retrieved",
    )


class OwnershipTransferResponse(BaseModel):
    """Response model for transfer_ownership() method.

    Documents the ownership transfer with involved parties and updated permissions.
    """

    model_config = ConfigDict(from_attributes=True)

    document: Document = Field(
        ..., description="Updated document with new owner information"
    )
    old_owner: UUID = Field(
        ..., description="Agent UUID of the previous document owner"
    )
    new_owner: UUID = Field(..., description="Agent UUID of the new document owner")
    transferred_by: UUID = Field(
        ...,
        description="Agent UUID who performed the transfer (must be old owner or admin)",
    )
    transferred_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when ownership transfer occurred",
    )
    new_permissions: List[DocumentACL] = Field(
        ...,
        description="Updated permission list after transfer (new owner should have ADMIN)",
    )
