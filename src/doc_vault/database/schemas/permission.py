"""
Pydantic schema for PermissionGrant (v2.1).

Used for type-safe permission granting in set_permissions() method.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class PermissionGrant(BaseModel):
    """
    Permission grant for set_permissions().

    Represents a single permission to grant to an agent.
    Provides type safety and validation for permission operations.
    """

    agent_id: UUID | str = Field(
        ..., description="Agent UUID (as UUID object or string)"
    )
    permission: str = Field(
        ..., description="Permission level: READ, WRITE, DELETE, SHARE, or ADMIN"
    )
    expires_at: Optional[datetime] = Field(
        None, description="Optional expiration datetime"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Optional custom metadata for this permission"
    )

    @field_validator("permission")
    @classmethod
    def validate_permission(cls, v: str) -> str:
        """Validate that permission is one of the allowed values."""
        allowed = ["READ", "WRITE", "DELETE", "SHARE", "ADMIN"]
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f"Permission must be one of {allowed}, got '{v}'")
        return v_upper

    @field_validator("agent_id")
    @classmethod
    def validate_agent_id(cls, v: UUID | str) -> UUID | str:
        """Validate that agent_id is a valid UUID string if provided as string."""
        if isinstance(v, str):
            try:
                # Test if it's a valid UUID string
                UUID(v)
            except (ValueError, TypeError):
                raise ValueError(f"agent_id must be a valid UUID string, got '{v}'")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "agent_id": "550e8400-e29b-41d4-a716-446655440000",
                    "permission": "READ",
                },
                {
                    "agent_id": "550e8400-e29b-41d4-a716-446655440001",
                    "permission": "WRITE",
                    "expires_at": "2026-01-01T00:00:00Z",
                },
                {
                    "agent_id": "550e8400-e29b-41d4-a716-446655440002",
                    "permission": "ADMIN",
                    "metadata": {"granted_reason": "project lead"},
                },
            ]
        }
    }
