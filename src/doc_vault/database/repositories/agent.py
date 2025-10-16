"""
Agent repository for DocVault.

Provides CRUD operations for agents table.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from doc_vault.database.postgres_manager import PostgreSQLManager
from doc_vault.database.repositories.base import BaseRepository
from doc_vault.database.schemas.agent import Agent, AgentCreate

logger = logging.getLogger(__name__)


class AgentRepository(BaseRepository[Agent]):
    """
    Repository for Agent entities.

    Provides CRUD operations and agent-specific queries.
    """

    @property
    def table_name(self) -> str:
        """Database table name."""
        return "agents"

    @property
    def model_class(self) -> type:
        """Pydantic model class for this repository."""
        return Agent

    def _row_to_model(self, row: Dict[str, Any]) -> Agent:
        """
        Convert database row dict to Agent model.

        Args:
            row: Database row as dict

        Returns:
            Agent instance
        """
        return Agent(
            id=row["id"],
            external_id=row["external_id"],
            organization_id=row["organization_id"],
            name=row["name"],
            email=row["email"],
            agent_type=row["agent_type"],
            metadata=row["metadata"] or {},
            is_active=row["is_active"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _model_to_dict(self, model: Agent) -> Dict[str, Any]:
        """
        Convert Agent model to database dict.

        Args:
            model: Agent instance

        Returns:
            Dict suitable for database insertion/update
        """
        data = {
            "external_id": model.external_id,
            "organization_id": str(model.organization_id),
            "name": model.name,
            "email": model.email,
            "agent_type": model.agent_type,
            "metadata": model.metadata,
            "is_active": model.is_active,
        }

        # Include ID if it exists (for updates)
        if hasattr(model, "id") and model.id:
            data["id"] = str(model.id)

        return data

    async def get_by_external_id(self, external_id: str) -> Optional[Agent]:
        """
        Get an agent by its external ID.

        Args:
            external_id: External system identifier

        Returns:
            Agent instance or None if not found
        """
        try:
            query = "SELECT * FROM agents WHERE external_id = $1"
            result = await self.db_manager.execute(query, [external_id])

            rows = result.result()
            if not rows:
                return None

            return self._row_to_model(rows[0])

        except Exception as e:
            logger.error(f"Failed to get agent by external_id {external_id}: {e}")
            from doc_vault.exceptions import DatabaseError

            raise DatabaseError("Failed to get agent by external ID") from e

    async def get_by_organization(
        self, organization_id: UUID, limit: int = 100, offset: int = 0
    ) -> List[Agent]:
        """
        Get all agents for an organization.

        Args:
            organization_id: Organization UUID
            limit: Maximum number of agents to return
            offset: Number of agents to skip

        Returns:
            List of Agent instances
        """
        try:
            query = """
                SELECT * FROM agents
                WHERE organization_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
            """
            result = await self.db_manager.execute(
                query, [str(organization_id), limit, offset]
            )

            rows = result.result()
            return [self._row_to_model(row) for row in rows]

        except Exception as e:
            logger.error(
                f"Failed to get agents for organization {organization_id}: {e}"
            )
            from doc_vault.exceptions import DatabaseError

            raise DatabaseError("Failed to get agents for organization") from e

    async def get_active_by_organization(self, organization_id: UUID) -> List[Agent]:
        """
        Get all active agents for an organization.

        Args:
            organization_id: Organization UUID

        Returns:
            List of active Agent instances
        """
        try:
            query = """
                SELECT * FROM agents
                WHERE organization_id = $1 AND is_active = true
                ORDER BY created_at DESC
            """
            result = await self.db_manager.execute(query, [str(organization_id)])

            rows = result.result()
            return [self._row_to_model(row) for row in rows]

        except Exception as e:
            logger.error(
                f"Failed to get active agents for organization {organization_id}: {e}"
            )
            from doc_vault.exceptions import DatabaseError

            raise DatabaseError("Failed to get active agents for organization") from e

    async def create_from_create_schema(self, create_data: AgentCreate) -> Agent:
        """
        Create an agent from AgentCreate schema.

        This is a convenience method that handles the conversion from
        create schema to full model.

        Args:
            create_data: AgentCreate schema instance

        Returns:
            Created Agent instance
        """
        try:
            # Convert create schema to dict
            data = create_data.model_dump()

            # Build column names and values for insert
            columns = list(data.keys())
            values = list(data.values())

            # Build the query with string interpolation for UUIDs
            column_list = ", ".join(columns)
            value_list = []
            for val in values:
                if isinstance(val, UUID):
                    value_list.append(f"'{str(val)}'")
                elif isinstance(val, str):
                    # Escape single quotes in strings
                    escaped_val = val.replace("'", "''")
                    value_list.append(f"'{escaped_val}'")
                elif isinstance(val, bool):
                    value_list.append("true" if val else "false")
                elif isinstance(val, dict):
                    # JSONB values
                    import json

                    value_list.append(f"'{json.dumps(val)}'")
                elif val is None:
                    value_list.append("NULL")
                else:
                    value_list.append(str(val))

            query = f"""
                INSERT INTO {self.table_name} ({column_list})
                VALUES ({', '.join(value_list)})
                RETURNING *
            """

            result = await self.db_manager.execute(query)
            row = result.result()[0]  # First (and only) row

            return self._row_to_model(row)

        except Exception as e:
            logger.error(f"Failed to create agent: {e}")
            from doc_vault.exceptions import DatabaseError

            raise DatabaseError("Failed to create agent") from e
