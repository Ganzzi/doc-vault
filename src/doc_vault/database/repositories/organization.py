"""
Organization repository for DocVault.

Provides CRUD operations for organizations table.

v2.0 Changes:
- Organizations use external UUIDs as primary keys (no external_id field)
- Removed name field (managed externally)
- Removed get_by_external_id() method
- Updated to use pure UUID-based lookups
"""

import logging
from typing import Any, Dict
from uuid import UUID

from doc_vault.database.repositories.base import BaseRepository
from doc_vault.database.schemas.organization import Organization, OrganizationCreate
from doc_vault.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class OrganizationRepository(BaseRepository[Organization]):
    """
    Repository for Organization entities.

    v2.0: Provides UUID-based CRUD operations for organizations.
    Organizations are pure reference entities with only UUID and metadata.
    """

    @property
    def table_name(self) -> str:
        """Database table name."""
        return "organizations"

    @property
    def model_class(self) -> type:
        """Pydantic model class for this repository."""
        return Organization

    def _row_to_model(self, row: Dict[str, Any]) -> Organization:
        """
        Convert database row dict to Organization model.

        Args:
            row: Database row as dict

        Returns:
            Organization instance
        """
        return Organization(
            id=row["id"],
            metadata=row["metadata"] or {},
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _model_to_dict(self, model: Organization) -> Dict[str, Any]:
        """
        Convert Organization model to database dict.

        Args:
            model: Organization instance

        Returns:
            Dict suitable for database insertion/update
        """
        data = {
            "id": model.id,
            "metadata": model.metadata,
        }

        return data

    async def create(self, create_data: OrganizationCreate) -> Organization:
        """
        Create an organization with external UUID.

        v2.0: ID is provided by caller (external system UUID).

        Args:
            create_data: OrganizationCreate schema with id and metadata

        Returns:
            Created Organization instance

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

            logger.debug(f"Creating organization: {query}")

            result = await self.db_manager.execute(query, values)
            row = result.result()[0]  # First (and only) row

            return self._row_to_model(row)

        except Exception as e:
            logger.error(f"Failed to create organization: {e}")
            raise DatabaseError("Failed to create organization") from e

    async def delete(self, org_id: UUID, force: bool = False) -> bool:
        """
        Delete an organization.

        v2.0: Organizations cascade-delete their agents and documents.

        Args:
            org_id: Organization UUID to delete
            force: If True, delete even if it has related entities (cascading)
                   If False, check first and raise error if entities exist

        Returns:
            True if deleted, False if not found

        Raises:
            DatabaseError: If deletion fails or entities exist (if force=False)
        """
        try:
            org_id = self._ensure_uuid(org_id)

            if not force:
                # Check for agents
                agents_query = (
                    "SELECT COUNT(*) as count FROM agents WHERE organization_id = $1"
                )
                agents_result = await self.db_manager.execute(agents_query, [org_id])
                agent_count = agents_result.result()[0]["count"]

                if agent_count > 0:
                    raise DatabaseError(
                        f"Cannot delete organization with {agent_count} agent(s). "
                        "Use force=True to cascade delete."
                    )

                # Check for documents
                docs_query = (
                    "SELECT COUNT(*) as count FROM documents WHERE organization_id = $1"
                )
                docs_result = await self.db_manager.execute(docs_query, [org_id])
                doc_count = docs_result.result()[0]["count"]

                if doc_count > 0:
                    raise DatabaseError(
                        f"Cannot delete organization with {doc_count} document(s). "
                        "Use force=True to cascade delete."
                    )

            # Delete organization (cascade delete handled by foreign key constraints)
            query = "DELETE FROM organizations WHERE id = $1"
            await self.db_manager.execute(query, [org_id])

            return True

        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Failed to delete organization {org_id}: {e}")
            raise DatabaseError("Failed to delete organization") from e
