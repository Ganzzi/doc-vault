"""
Pydantic schemas for Document entity.

v2.0 Changes:
- Added prefix field for hierarchical document organization
- Added path field for computed hierarchical path
- prefix and path support recursive listing and filtering
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DocumentBase(BaseModel):
    """Base schema for Document entity."""

    organization_id: UUID = Field(..., description="Organization UUID")
    name: str = Field(..., description="Document display name")
    description: Optional[str] = Field(None, description="Document description")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes", ge=0)
    mime_type: Optional[str] = Field(None, description="MIME type")
    storage_path: str = Field(..., description="S3/MinIO storage path")
    prefix: Optional[str] = Field(
        None,
        description="Hierarchical prefix for document organization (e.g., '/reports/2025/q1/')",
    )
    path: Optional[str] = Field(
        None, description="Full hierarchical path including document name"
    )
    current_version: int = Field(default=1, description="Current version number", ge=1)
    status: str = Field(
        default="active",
        description="Document status",
        pattern="^(draft|active|archived|deleted)$",
    )
    created_by: UUID = Field(..., description="Agent who created the document")
    updated_by: Optional[UUID] = Field(
        None, description="Agent who last updated the document"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    tags: List[str] = Field(default_factory=list, description="Document tags")

    @field_validator("prefix")
    @classmethod
    def validate_prefix(cls, v: Optional[str]) -> Optional[str]:
        """Validate prefix format: should be lowercase with slashes."""
        if v is None:
            return v
        if not v.startswith("/"):
            raise ValueError("Prefix must start with /")
        if not v.endswith("/"):
            raise ValueError("Prefix must end with /")
        if "//" in v:
            raise ValueError("Prefix cannot contain consecutive slashes")
        return v

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: Optional[str]) -> Optional[str]:
        """Validate path format: should be non-empty if provided."""
        if v is None:
            return v
        if not v.strip():
            raise ValueError("Path cannot be empty")
        return v


class DocumentCreate(BaseModel):
    """Schema for creating a new document."""

    id: Optional[UUID] = Field(
        None, description="Document UUID (optional, generated if not provided)"
    )
    organization_id: UUID = Field(..., description="Organization UUID")
    name: str = Field(..., description="Document display name")
    description: Optional[str] = Field(None, description="Document description")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes", ge=0)
    mime_type: Optional[str] = Field(None, description="MIME type")
    storage_path: str = Field(..., description="S3/MinIO storage path")
    prefix: Optional[str] = Field(
        None, description="Hierarchical prefix for document organization"
    )
    path: Optional[str] = Field(
        None,
        description="Full hierarchical path (auto-generated from prefix + name if not provided)",
    )
    current_version: int = Field(default=1, description="Current version number", ge=1)
    status: str = Field(default="active", description="Document status")
    created_by: UUID = Field(..., description="Agent who created the document")
    updated_by: Optional[UUID] = Field(
        None, description="Agent who last updated the document"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    tags: List[str] = Field(default_factory=list, description="Document tags")

    @field_validator("prefix")
    @classmethod
    def validate_prefix(cls, v: Optional[str]) -> Optional[str]:
        """Validate prefix format: should be lowercase with slashes."""
        if v is None:
            return v
        if not v.startswith("/"):
            raise ValueError("Prefix must start with /")
        if not v.endswith("/"):
            raise ValueError("Prefix must end with /")
        if "//" in v:
            raise ValueError("Prefix cannot contain consecutive slashes")
        return v


class DocumentUpdate(BaseModel):
    """Schema for updating a document."""

    name: Optional[str] = Field(None, description="Document display name")
    description: Optional[str] = Field(None, description="Document description")
    filename: Optional[str] = Field(None, description="Original filename")
    file_size: Optional[int] = Field(None, description="File size in bytes", ge=0)
    mime_type: Optional[str] = Field(None, description="MIME type")
    storage_path: Optional[str] = Field(None, description="S3/MinIO storage path")
    prefix: Optional[str] = Field(None, description="Hierarchical prefix")
    path: Optional[str] = Field(None, description="Full hierarchical path")
    current_version: Optional[int] = Field(
        None, description="Current version number", ge=1
    )
    status: Optional[str] = Field(
        None, description="Document status", pattern="^(draft|active|archived|deleted)$"
    )
    updated_by: Optional[UUID] = Field(
        None, description="Agent who last updated the document"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    tags: Optional[List[str]] = Field(None, description="Document tags")

    @field_validator("prefix")
    @classmethod
    def validate_prefix(cls, v: Optional[str]) -> Optional[str]:
        """Validate prefix format."""
        if v is None:
            return v
        if not v.startswith("/"):
            raise ValueError("Prefix must start with /")
        if not v.endswith("/"):
            raise ValueError("Prefix must end with /")
        if "//" in v:
            raise ValueError("Prefix cannot contain consecutive slashes")
        return v


class Document(DocumentBase):
    """Full schema for Document entity including database fields."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4, description="Internal UUID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
