"""
Pydantic schemas for DocumentACL entity.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict


class DocumentACLBase(BaseModel):
    """Base schema for DocumentACL entity."""

    document_id: UUID = Field(..., description="Document UUID")
    agent_id: UUID = Field(..., description="Agent UUID")
    permission: str = Field(
        ..., description="Permission type", pattern="^(READ|WRITE|DELETE|SHARE|ADMIN)$"
    )
    granted_by: UUID = Field(..., description="Agent who granted the permission")
    expires_at: Optional[datetime] = Field(
        None, description="Optional expiration timestamp"
    )


class DocumentACLCreate(DocumentACLBase):
    """Schema for creating a new document ACL entry."""

    pass


class DocumentACLUpdate(BaseModel):
    """Schema for updating a document ACL entry."""

    permission: Optional[str] = Field(
        None, description="Permission type", pattern="^(READ|WRITE|DELETE|SHARE|ADMIN)$"
    )
    expires_at: Optional[datetime] = Field(
        None, description="Optional expiration timestamp"
    )


class DocumentACL(DocumentACLBase):
    """Full schema for DocumentACL entity including database fields."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4, description="Internal UUID")
    granted_at: datetime = Field(..., description="When permission was granted")
