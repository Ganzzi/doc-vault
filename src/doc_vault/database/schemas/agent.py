"""
Pydantic schemas for Agent entity.

v2.0 Changes:
- Agents use external UUIDs as primary keys
- Removed internal_id/external_id duplication
- Removed name, email, agent_type (managed externally)
- Agent ID is now the external UUID provided by the caller
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class AgentBase(BaseModel):
    """Base schema for Agent entity (v2.0)."""

    organization_id: UUID = Field(..., description="Organization UUID")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    is_active: bool = Field(default=True, description="Whether agent is active")


class AgentCreate(BaseModel):
    """Schema for creating a new agent.

    v2.0: ID must be provided by caller (external UUID).
    Name, email, and agent_type are managed externally.
    """

    id: UUID = Field(..., description="Agent UUID (from external system)")
    organization_id: UUID = Field(..., description="Organization UUID")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    is_active: bool = Field(default=True, description="Whether agent is active")


class AgentUpdate(BaseModel):
    """Schema for updating an agent."""

    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    is_active: Optional[bool] = Field(None, description="Whether agent is active")


class Agent(BaseModel):
    """Full schema for Agent entity including database fields (v2.0).

    v2.0 Model:
    - id: External UUID (provided at creation)
    - organization_id: Organization this agent belongs to
    - metadata: Optional additional data
    - is_active: Whether agent is active
    - timestamps: Automatic database timestamps

    Example:
        agent = Agent(
            id=UUID("550e8400-e29b-41d4-a716-446655440000"),
            organization_id=UUID("550e8400-e29b-41d4-a716-446655440001"),
            metadata={"role": "manager"},
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Agent UUID (external reference)")
    organization_id: UUID = Field(..., description="Organization UUID")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    is_active: bool = Field(default=True, description="Whether agent is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
