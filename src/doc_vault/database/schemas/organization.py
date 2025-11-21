"""
Pydantic schemas for DocVault database entities.

This module defines Pydantic BaseModel classes for all database entities,
providing type safety and validation for data transfer between layers.

v2.0 Changes:
- Organizations and Agents use external UUIDs as primary keys
- Removed internal_id/external_id duplication
- Organization ID is now the external UUID provided by the caller
- Name and other entity details are managed externally
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OrganizationBase(BaseModel):
    """Base schema for Organization entity (v2.0)."""

    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class OrganizationCreate(BaseModel):
    """Schema for creating a new organization.

    v2.0: ID must be provided by caller (external UUID).
    """

    id: UUID = Field(..., description="Organization UUID (from external system)")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class OrganizationUpdate(BaseModel):
    """Schema for updating an organization."""

    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class Organization(BaseModel):
    """Full schema for Organization entity including database fields (v2.0).

    v2.0 Model:
    - id: External UUID (provided at creation)
    - metadata: Optional additional data
    - timestamps: Automatic database timestamps

    Example:
        org = Organization(
            id=UUID("550e8400-e29b-41d4-a716-446655440000"),
            metadata={"department": "engineering"},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Organization UUID (external reference)")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
