"""
Pydantic schemas for Agent entity.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict


class AgentBase(BaseModel):
    """Base schema for Agent entity."""

    external_id: str = Field(..., description="External system identifier")
    organization_id: UUID = Field(..., description="Organization UUID")
    name: str = Field(..., description="Agent display name")
    email: Optional[str] = Field(None, description="Agent email address")
    agent_type: str = Field(
        default="human", description="Agent type", pattern="^(human|ai|service)$"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    is_active: bool = Field(default=True, description="Whether agent is active")


class AgentCreate(AgentBase):
    """Schema for creating a new agent."""

    pass


class AgentUpdate(BaseModel):
    """Schema for updating an agent."""

    name: Optional[str] = Field(None, description="Agent display name")
    email: Optional[str] = Field(None, description="Agent email address")
    agent_type: Optional[str] = Field(
        None, description="Agent type", pattern="^(human|ai|service)$"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    is_active: Optional[bool] = Field(None, description="Whether agent is active")


class Agent(AgentBase):
    """Full schema for Agent entity including database fields."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4, description="Internal UUID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
