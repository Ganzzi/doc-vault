"""
Document repository for DocVault.

Provides CRUD operations for documents table.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from doc_vault.database.postgres_manager import PostgreSQLManager
from doc_vault.database.repositories.base import BaseRepository
from doc_vault.database.schemas.document import Document, DocumentCreate

logger = logging.getLogger(__name__)


class DocumentRepository(BaseRepository[Document]):
    """
    Repository for Document entities.

    Provides CRUD operations and document-specific queries.
    """

    @property
    def table_name(self) -> str:
        """Database table name."""
        return "documents"

    @property
    def model_class(self) -> type:
        """Pydantic model class for this repository."""
        return Document

    def _row_to_model(self, row: Dict[str, Any]) -> Document:
        """
        Convert database row dict to Document model.

        Args:
            row: Database row as dict

        Returns:
            Document instance
        """
        return Document(
            id=row["id"],
            organization_id=row["organization_id"],
            name=row["name"],
            description=row["description"],
            filename=row["filename"],
            file_size=row["file_size"],
            mime_type=row["mime_type"],
            storage_path=row["storage_path"],
            current_version=row["current_version"],
            status=row["status"],
            created_by=row["created_by"],
            updated_by=row["updated_by"],
            metadata=row["metadata"] or {},
            tags=row["tags"] or [],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _model_to_dict(self, model: Document) -> Dict[str, Any]:
        """
        Convert Document model to database dict.

        Args:
            model: Document instance

        Returns:
            Dict suitable for database insertion/update
        """
        data = {
            "organization_id": str(model.organization_id),
            "name": model.name,
            "description": model.description,
            "filename": model.filename,
            "file_size": model.file_size,
            "mime_type": model.mime_type,
            "storage_path": model.storage_path,
            "current_version": model.current_version,
            "status": model.status,
            "created_by": str(model.created_by),
            "updated_by": str(model.updated_by) if model.updated_by else None,
            "metadata": model.metadata,
            "tags": model.tags,
        }

        # Include ID if it exists (for updates)
        if hasattr(model, "id") and model.id:
            data["id"] = str(model.id)

        return data

    async def get_by_organization(
        self,
        organization_id: UUID,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Document]:
        """
        Get documents for an organization.

        Args:
            organization_id: Organization UUID
            status: Optional status filter ('active', 'draft', 'archived', 'deleted')
            limit: Maximum number of documents to return
            offset: Number of documents to skip

        Returns:
            List of Document instances
        """
        try:
            query = """
                SELECT * FROM documents
                WHERE organization_id = $1
            """
            params = [str(organization_id)]
            param_index = 2

            if status:
                query += f" AND status = ${param_index}"
                params.append(status)
                param_index += 1

            query += f" ORDER BY created_at DESC LIMIT ${param_index} OFFSET ${param_index + 1}"
            params.extend([limit, offset])

            result = await self.db_manager.execute(query, params)
            rows = result.result()
            return [self._row_to_model(row) for row in rows]

        except Exception as e:
            logger.error(
                f"Failed to get documents for organization {organization_id}: {e}"
            )
            from doc_vault.exceptions import DatabaseError

            raise DatabaseError("Failed to get documents for organization") from e

    async def get_by_created_by(
        self,
        agent_id: UUID,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Document]:
        """
        Get documents created by an agent.

        Args:
            agent_id: Agent UUID
            status: Optional status filter
            limit: Maximum number of documents to return
            offset: Number of documents to skip

        Returns:
            List of Document instances
        """
        try:
            query = """
                SELECT * FROM documents
                WHERE created_by = $1
            """
            params = [str(agent_id)]
            param_index = 2

            if status:
                query += f" AND status = ${param_index}"
                params.append(status)
                param_index += 1

            query += f" ORDER BY created_at DESC LIMIT ${param_index} OFFSET ${param_index + 1}"
            params.extend([limit, offset])

            result = await self.db_manager.execute(query, params)
            rows = result.result()
            return [self._row_to_model(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get documents created by agent {agent_id}: {e}")
            from doc_vault.exceptions import DatabaseError

            raise DatabaseError("Failed to get documents created by agent") from e

    async def search_by_name(
        self, organization_id: UUID, name_query: str, limit: int = 50
    ) -> List[Document]:
        """
        Search documents by name within an organization.

        Args:
            organization_id: Organization UUID
            name_query: Search query for document name
            limit: Maximum number of results

        Returns:
            List of Document instances
        """
        try:
            query = """
                SELECT * FROM documents
                WHERE organization_id = $1
                  AND name ILIKE $2
                  AND status = 'active'
                ORDER BY created_at DESC
                LIMIT $3
            """
            result = await self.db_manager.execute(
                query, [str(organization_id), f"%{name_query}%", limit]
            )
            rows = result.result()
            return [self._row_to_model(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to search documents by name '{name_query}': {e}")
            from doc_vault.exceptions import DatabaseError

            raise DatabaseError("Failed to search documents by name") from e

    async def get_by_tags(
        self, organization_id: UUID, tags: List[str], limit: int = 100, offset: int = 0
    ) -> List[Document]:
        """
        Get documents that have any of the specified tags.

        Args:
            organization_id: Organization UUID
            tags: List of tags to search for
            limit: Maximum number of documents to return
            offset: Number of documents to skip

        Returns:
            List of Document instances
        """
        try:
            # Use array overlap operator && for tag matching
            query = """
                SELECT * FROM documents
                WHERE organization_id = $1
                  AND tags && $2
                  AND status = 'active'
                ORDER BY created_at DESC
                LIMIT $3 OFFSET $4
            """
            result = await self.db_manager.execute(
                query, [str(organization_id), tags, limit, offset]
            )
            rows = result.result()
            return [self._row_to_model(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get documents by tags {tags}: {e}")
            from doc_vault.exceptions import DatabaseError

            raise DatabaseError("Failed to get documents by tags") from e

    async def update_status(
        self, document_id: UUID, status: str, updated_by: UUID
    ) -> Optional[Document]:
        """
        Update document status.

        Args:
            document_id: Document UUID
            status: New status ('draft', 'active', 'archived', 'deleted')
            updated_by: Agent making the change

        Returns:
            Updated Document instance or None if not found
        """
        try:
            updates = {"status": status, "updated_by": str(updated_by)}
            return await self.update(document_id, updates)

        except Exception as e:
            logger.error(
                f"Failed to update document {document_id} status to {status}: {e}"
            )
            from doc_vault.exceptions import DatabaseError

            raise DatabaseError("Failed to update document status") from e

    async def increment_version(
        self, document_id: UUID, updated_by: UUID
    ) -> Optional[Document]:
        """
        Increment the current version of a document.

        Args:
            document_id: Document UUID
            updated_by: Agent making the change

        Returns:
            Updated Document instance or None if not found
        """
        try:
            # Get current document to increment version
            document = await self.get_by_id(document_id)
            if not document:
                return None

            updates = {
                "current_version": document.current_version + 1,
                "updated_by": str(updated_by),
            }
            return await self.update(document_id, updates)

        except Exception as e:
            logger.error(f"Failed to increment version for document {document_id}: {e}")
            from doc_vault.exceptions import DatabaseError

            raise DatabaseError("Failed to increment document version") from e

    async def create_from_create_schema(self, create_data: DocumentCreate) -> Document:
        """
        Create a document from DocumentCreate schema.

        This is a convenience method that handles the conversion from
        create schema to full model.

        Args:
            create_data: DocumentCreate schema instance

        Returns:
            Created Document instance
        """
        try:
            # Convert create schema to dict
            data = create_data.model_dump()

            # Handle optional ID
            if create_data.id is None:
                data.pop("id", None)  # Remove None ID so database generates it
            else:
                data["id"] = str(create_data.id)  # Convert UUID to string

            # Convert UUIDs to strings for psqlpy
            data["organization_id"] = str(create_data.organization_id)
            data["created_by"] = str(create_data.created_by)
            if create_data.updated_by:
                data["updated_by"] = str(create_data.updated_by)

            # Build column names and placeholders for insert
            columns = list(data.keys())
            placeholders = [f"${i+1}" for i in range(len(columns))]
            values = list(data.values())

            query = f"""
                INSERT INTO {self.table_name} ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
                RETURNING *
            """

            logger.debug(f"Creating document: {query}")

            result = await self.db_manager.execute(query, values)
            row = result.result()[0]  # First (and only) row

            return self._row_to_model(row)

        except Exception as e:
            logger.error(f"Failed to create document: {e}")
            from doc_vault.exceptions import DatabaseError

            raise DatabaseError("Failed to create document") from e
