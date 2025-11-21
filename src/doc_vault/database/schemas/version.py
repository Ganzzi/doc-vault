"""
Pydantic schemas for DocumentVersion entity.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class DocumentVersionBase(BaseModel):
    """Base schema for DocumentVersion entity."""

    document_id: UUID = Field(..., description="Document UUID")
    version_number: int = Field(..., description="Version number", ge=1)
    filename: str = Field(..., description="Version filename")
    file_size: int = Field(..., description="File size in bytes", ge=0)
    storage_path: str = Field(..., description="S3/MinIO storage path")
    mime_type: Optional[str] = Field(None, description="MIME type")
    change_description: Optional[str] = Field(
        None, description="Description of changes"
    )
    change_type: Optional[str] = Field(
        None, description="Type of change", pattern="^(create|update|restore)$"
    )
    created_by: UUID = Field(..., description="Agent who created this version")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Version-specific metadata"
    )


class DocumentVersionCreate(DocumentVersionBase):
    """Schema for creating a new document version."""

    pass


class DocumentVersionUpdate(BaseModel):
    """Schema for updating a document version."""

    filename: Optional[str] = Field(None, description="Version filename")
    file_size: Optional[int] = Field(None, description="File size in bytes", ge=0)
    storage_path: Optional[str] = Field(None, description="S3/MinIO storage path")
    mime_type: Optional[str] = Field(None, description="MIME type")
    change_description: Optional[str] = Field(
        None, description="Description of changes"
    )
    change_type: Optional[str] = Field(
        None, description="Type of change", pattern="^(create|update|restore)$"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Version-specific metadata"
    )


class DocumentVersion(DocumentVersionBase):
    """Full schema for DocumentVersion entity including database fields."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4, description="Internal UUID")
    created_at: datetime = Field(..., description="Creation timestamp")
