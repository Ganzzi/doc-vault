"""
Agent repository for DocVault.

Provides CRUD operations for agents table.

v2.0 Changes:
- Agents use external UUIDs as primary keys (no external_id field)
- Removed name, email, agent_type fields (managed externally)
- Removed get_by_external_id() method
- Updated to use pure UUID-based lookups
- Added remove_from_organization() method for explicit removal
"""

import logging
from typing import Any, Dict, List
from uuid import UUID

from doc_vault.database.repositories.base import BaseRepository
from doc_vault.database.schemas.agent import Agent, AgentCreate
from doc_vault.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class AgentRepository(BaseRepository[Agent]):
    """
    Repository for Agent entities.

    v2.0: Provides UUID-based CRUD operations for agents.
    Agents are pure reference entities with UUID, organization reference, and metadata.
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
            organization_id=row["organization_id"],
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
            "id": model.id,
            "organization_id": model.organization_id,
            "metadata": model.metadata,
            "is_active": model.is_active,
        }

        return data

    async def create(self, create_data: AgentCreate) -> Agent:
        """
        Create an agent with external UUID.

        v2.0: ID is provided by caller (external system UUID).

        Args:
            create_data: AgentCreate schema with id, organization_id, and metadata

        Returns:
            Created Agent instance

        Raises:
            DatabaseError: If creation fails
        """
        try:
            data = create_data.model_dump()

            # Build column names and placeholders for insert
            columns = list(data.keys())
            placeholders = [f"${i+1}" for i in range(len(columns))]
            values = list(data.values())

            query = f"""
                INSERT INTO {self.table_name} ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
                RETURNING *
            """

            logger.debug(f"Creating agent: {query}")

            result = await self.db_manager.execute(query, values)
            row = result.result()[0]  # First (and only) row

            return self._row_to_model(row)

        except Exception as e:
            logger.error(f"Failed to create agent: {e}")
            raise DatabaseError("Failed to create agent") from e

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
            organization_id = self._ensure_uuid(organization_id)

            query = """
                SELECT * FROM agents
                WHERE organization_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
            """
            result = await self.db_manager.execute(
                query, [organization_id, limit, offset]
            )

            rows = result.result()
            return [self._row_to_model(row) for row in rows]

        except Exception as e:
            logger.error(
                f"Failed to get agents for organization {organization_id}: {e}"
            )
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
            organization_id = self._ensure_uuid(organization_id)

            query = """
                SELECT * FROM agents
                WHERE organization_id = $1 AND is_active = true
                ORDER BY created_at DESC
            """
            result = await self.db_manager.execute(query, [organization_id])

            rows = result.result()
            return [self._row_to_model(row) for row in rows]

        except Exception as e:
            logger.error(
                f"Failed to get active agents for organization {organization_id}: {e}"
            )
            raise DatabaseError("Failed to get active agents for organization") from e

    async def delete(self, agent_id: UUID, force: bool = False) -> bool:
        """
        Delete an agent.

        v2.0: Agents cascade-delete their created documents and versions.

        Args:
            agent_id: Agent UUID to delete
            force: If True, delete even if it has related entities (cascading)
                   If False, check first and raise error if entities exist

        Returns:
            True if deleted, False if not found

        Raises:
            DatabaseError: If deletion fails or entities exist (if force=False)
        """
        try:
            agent_id = self._ensure_uuid(agent_id)

            if not force:
                # Check for documents created by this agent
                docs_query = (
                    "SELECT COUNT(*) as count FROM documents WHERE created_by = $1"
                )
                docs_result = await self.db_manager.execute(docs_query, [agent_id])
                doc_count = docs_result.result()[0]["count"]

                if doc_count > 0:
                    raise DatabaseError(
                        f"Cannot delete agent with {doc_count} document(s) created. "
                        "Use force=True to cascade delete."
                    )

                # Check for ACL permissions granted to this agent
                acl_query = (
                    "SELECT COUNT(*) as count FROM document_acl WHERE agent_id = $1"
                )
                acl_result = await self.db_manager.execute(acl_query, [agent_id])
                acl_count = acl_result.result()[0]["count"]

                if acl_count > 0:
                    raise DatabaseError(
                        f"Cannot delete agent with {acl_count} permission(s) granted. "
                        "Use force=True to cascade delete."
                    )

            # Delete agent (cascade delete handled by foreign key constraints)
            query = "DELETE FROM agents WHERE id = $1"
            await self.db_manager.execute(query, [agent_id])

            return True

        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Failed to delete agent {agent_id}: {e}")
            raise DatabaseError("Failed to delete agent") from e

    async def remove_from_organization(self, agent_id: UUID) -> bool:
        """
        Remove an agent from their organization (soft delete).

        Sets is_active to false without deleting the record.

        Args:
            agent_id: Agent UUID

        Returns:
            True if updated, False if not found
        """
        try:
            agent_id = self._ensure_uuid(agent_id)

            query = """
                UPDATE agents
                SET is_active = false, updated_at = NOW()
                WHERE id = $1
                RETURNING id
            """
            result = await self.db_manager.execute(query, [agent_id])

            rows = result.result()
            return len(rows) > 0

        except Exception as e:
            logger.error(f"Failed to remove agent {agent_id}: {e}")
            raise DatabaseError("Failed to remove agent from organization") from e
