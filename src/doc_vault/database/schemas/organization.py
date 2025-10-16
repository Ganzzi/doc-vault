"""
Pydantic schemas for DocVault database entities.

This module defines Pydantic BaseModel classes for all database entities,
providing type safety and validation for data transfer between layers.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict


class OrganizationBase(BaseModel):
    """Base schema for Organization entity."""

    external_id: str = Field(..., description="External system identifier")
    name: str = Field(..., description="Organization display name")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class OrganizationCreate(OrganizationBase):
    """Schema for creating a new organization."""

    pass


class OrganizationUpdate(BaseModel):
    """Schema for updating an organization."""

    name: Optional[str] = Field(None, description="Organization display name")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class Organization(OrganizationBase):
    """Full schema for Organization entity including database fields."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4, description="Internal UUID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
