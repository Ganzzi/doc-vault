"""
Pydantic schemas for Document entity.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict


class DocumentBase(BaseModel):
    """Base schema for Document entity."""

    organization_id: UUID = Field(..., description="Organization UUID")
    name: str = Field(..., description="Document display name")
    description: Optional[str] = Field(None, description="Document description")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes", ge=0)
    mime_type: Optional[str] = Field(None, description="MIME type")
    storage_path: str = Field(..., description="S3/MinIO storage path")
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


class DocumentCreate(DocumentBase):
    """Schema for creating a new document."""

    id: Optional[UUID] = Field(
        None, description="Document UUID (optional, generated if not provided)"
    )

    pass


class DocumentUpdate(BaseModel):
    """Schema for updating a document."""

    name: Optional[str] = Field(None, description="Document display name")
    description: Optional[str] = Field(None, description="Document description")
    filename: Optional[str] = Field(None, description="Original filename")
    file_size: Optional[int] = Field(None, description="File size in bytes", ge=0)
    mime_type: Optional[str] = Field(None, description="MIME type")
    storage_path: Optional[str] = Field(None, description="S3/MinIO storage path")
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


class Document(DocumentBase):
    """Full schema for Document entity including database fields."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4, description="Internal UUID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
