"""
Organization repository for DocVault.

Provides CRUD operations for organizations table.
"""

import logging
from typing import Any, Dict, Optional
from uuid import UUID

from doc_vault.database.postgres_manager import PostgreSQLManager
from doc_vault.database.repositories.base import BaseRepository
from doc_vault.database.schemas.organization import Organization, OrganizationCreate

logger = logging.getLogger(__name__)


class OrganizationRepository(BaseRepository[Organization]):
    """
    Repository for Organization entities.

    Provides CRUD operations and organization-specific queries.
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
            external_id=row["external_id"],
            name=row["name"],
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
            "external_id": model.external_id,
            "name": model.name,
            "metadata": model.metadata,
        }

        # Include ID if it exists (for updates)
        if hasattr(model, "id") and model.id:
            data["id"] = str(model.id)

        return data

    async def get_by_external_id(self, external_id: str) -> Optional[Organization]:
        """
        Get an organization by its external ID.

        Args:
            external_id: External system identifier

        Returns:
            Organization instance or None if not found
        """
        try:
            query = "SELECT * FROM organizations WHERE external_id = $1"
            result = await self.db_manager.execute(query, [external_id])

            rows = result.result()
            if not rows:
                return None

            return self._row_to_model(rows[0])

        except Exception as e:
            logger.error(
                f"Failed to get organization by external_id {external_id}: {e}"
            )
            from doc_vault.exceptions import DatabaseError

            raise DatabaseError("Failed to get organization by external ID") from e

    async def create_from_create_schema(
        self, create_data: OrganizationCreate
    ) -> Organization:
        """
        Create an organization from OrganizationCreate schema.

        This is a convenience method that handles the conversion from
        create schema to full model.

        Args:
            create_data: OrganizationCreate schema instance

        Returns:
            Created Organization instance
        """
        try:
            # Convert create schema to dict
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
            from doc_vault.exceptions import DatabaseError

            raise DatabaseError("Failed to create organization") from e
