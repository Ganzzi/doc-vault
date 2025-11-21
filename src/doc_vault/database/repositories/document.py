"""
Document repository for DocVault.

Provides CRUD operations for documents table.

v2.0 Changes:
- Added prefix and path columns for hierarchical document organization
- Added list_by_prefix() method for prefix-based listing
- Added list_recursive() method for recursive listing with depth control
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from doc_vault.database.repositories.base import BaseRepository
from doc_vault.database.schemas.document import Document, DocumentCreate
from doc_vault.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class DocumentRepository(BaseRepository[Document]):
    """
    Repository for Document entities.

    v2.0: Provides CRUD operations and hierarchical prefix-based queries.
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
            prefix=row.get("prefix"),
            path=row.get("path"),
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
            "organization_id": model.organization_id,
            "name": model.name,
            "description": model.description,
            "filename": model.filename,
            "file_size": model.file_size,
            "mime_type": model.mime_type,
            "storage_path": model.storage_path,
            "prefix": model.prefix,
            "path": model.path,
            "current_version": model.current_version,
            "status": model.status,
            "created_by": model.created_by,
            "updated_by": model.updated_by,
            "metadata": model.metadata,
            "tags": model.tags,
        }

        # Include ID if it exists (for updates)
        if hasattr(model, "id") and model.id:
            data["id"] = model.id

        return data

    async def get_by_id(self, id: UUID | str) -> Optional[Document]:
        """
        Get a document by its UUID.
        Override base implementation to exclude search_vector column.

        Args:
            id: Document UUID or string

        Returns:
            Document instance or None if not found
        """
        try:
            # Ensure id is a UUID
            id = self._ensure_uuid(id)

            # Exclude search_vector column to avoid tsvector conversion issues
            columns = [
                "id",
                "organization_id",
                "name",
                "description",
                "filename",
                "file_size",
                "mime_type",
                "storage_path",
                "current_version",
                "status",
                "created_by",
                "updated_by",
                "metadata",
                "tags",
                "created_at",
                "updated_at",
            ]
            query = f"SELECT {', '.join(columns)} FROM {self.table_name} WHERE id = $1"
            result = await self.db_manager.execute(query, [id])

            rows = result.result()
            if not rows:
                return None

            return self._row_to_model(rows[0])

        except Exception as e:
            logger.error(f"Failed to get Document by id {id}: {e}")
            from doc_vault.exceptions import DatabaseError

            raise DatabaseError("Failed to get Document") from e

    async def update(self, id: UUID, updates: Dict[str, Any]) -> Optional[Document]:
        """
        Update a document by ID.
        Override base implementation to exclude search_vector column.

        Args:
            id: Document UUID
            updates: Dict of field updates

        Returns:
            Updated Document instance or None if not found
        """
        try:
            if not updates:
                # No updates provided, just return current record
                return await self.get_by_id(id)

            # Build SET clause
            set_parts = []
            values = []
            param_index = 1

            for key, value in updates.items():
                set_parts.append(f"{key} = ${param_index}")
                values.append(value)
                param_index += 1

            # Add ID parameter
            values.append(id)

            # Exclude search_vector column to avoid tsvector conversion issues
            columns = [
                "id",
                "organization_id",
                "name",
                "description",
                "filename",
                "file_size",
                "mime_type",
                "storage_path",
                "current_version",
                "status",
                "created_by",
                "updated_by",
                "metadata",
                "tags",
                "created_at",
                "updated_at",
            ]

            query = f"""
                UPDATE {self.table_name}
                SET {', '.join(set_parts)}, updated_at = NOW()
                WHERE id = ${param_index}
                RETURNING {', '.join(columns)}
            """

            logger.debug(f"Updating Document {id}: {query}")

            result = await self.db_manager.execute(query, values)
            rows = result.result()

            if not rows:
                return None

            return self._row_to_model(rows[0])

        except Exception as e:
            logger.error(f"Failed to update Document {id}: {e}")
            from doc_vault.exceptions import DatabaseError

            raise DatabaseError("Failed to update Document") from e

    async def get_by_organization(
        self,
        organization_id: UUID | str,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Document]:
        """
        Get documents for an organization.

        Args:
            organization_id: Organization UUID or string
            status: Optional status filter ('active', 'draft', 'archived', 'deleted')
            limit: Maximum number of documents to return
            offset: Number of documents to skip

        Returns:
            List of Document instances
        """
        try:
            # Ensure organization_id is a UUID
            organization_id = self._ensure_uuid(organization_id)

            # Exclude search_vector column to avoid tsvector conversion issues
            columns = [
                "id",
                "organization_id",
                "name",
                "description",
                "filename",
                "file_size",
                "mime_type",
                "storage_path",
                "current_version",
                "status",
                "created_by",
                "updated_by",
                "metadata",
                "tags",
                "created_at",
                "updated_at",
            ]
            query = f"""
                SELECT {', '.join(columns)} FROM documents
                WHERE organization_id = $1
            """
            params = [organization_id]
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
            # Exclude search_vector column to avoid tsvector conversion issues
            columns = [
                "id",
                "organization_id",
                "name",
                "description",
                "filename",
                "file_size",
                "mime_type",
                "storage_path",
                "current_version",
                "status",
                "created_by",
                "updated_by",
                "metadata",
                "tags",
                "created_at",
                "updated_at",
            ]
            query = f"""
                SELECT {', '.join(columns)} FROM documents
                WHERE created_by = $1
            """
            params = [agent_id]
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
        self, organization_id: UUID | str, name_query: str, limit: int = 50
    ) -> List[Document]:
        """
        Search documents by name within an organization.

        Args:
            organization_id: Organization UUID or string
            name_query: Search query for document name
            limit: Maximum number of results

        Returns:
            List of Document instances
        """
        try:
            # Ensure organization_id is a UUID
            organization_id = self._ensure_uuid(organization_id)

            # Exclude search_vector column to avoid tsvector conversion issues
            columns = [
                "id",
                "organization_id",
                "name",
                "description",
                "filename",
                "file_size",
                "mime_type",
                "storage_path",
                "current_version",
                "status",
                "created_by",
                "updated_by",
                "metadata",
                "tags",
                "created_at",
                "updated_at",
            ]
            query = f"""
                SELECT {', '.join(columns)} FROM documents
                WHERE organization_id = $1
                  AND name ILIKE $2
                  AND status = 'active'
                ORDER BY created_at DESC
                LIMIT $3
            """
            result = await self.db_manager.execute(
                query, [organization_id, f"%{name_query}%", limit]
            )
            rows = result.result()
            return [self._row_to_model(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to search documents by name '{name_query}': {e}")
            from doc_vault.exceptions import DatabaseError

            raise DatabaseError("Failed to search documents by name") from e

    async def get_by_tags(
        self,
        organization_id: UUID | str,
        tags: List[str],
        limit: int = 100,
        offset: int = 0,
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
            # Exclude search_vector column to avoid tsvector conversion issues
            columns = [
                "id",
                "organization_id",
                "name",
                "description",
                "filename",
                "file_size",
                "mime_type",
                "storage_path",
                "current_version",
                "status",
                "created_by",
                "updated_by",
                "metadata",
                "tags",
                "created_at",
                "updated_at",
            ]
            # Use array overlap operator && for tag matching
            query = f"""
                SELECT {', '.join(columns)} FROM documents
                WHERE organization_id = $1
                  AND tags && $2
                  AND status = 'active'
                ORDER BY created_at DESC
                LIMIT $3 OFFSET $4
            """
            result = await self.db_manager.execute(
                query, [organization_id, tags, limit, offset]
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
            updates = {"status": status, "updated_by": updated_by}
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
            # Keep UUIDs as UUID objects for psqlpy
            # data["organization_id"] = str(create_data.organization_id)
            # data["created_by"] = str(create_data.created_by)
            # if create_data.updated_by:
            #     data["updated_by"] = str(create_data.updated_by)

            # Build column names and placeholders for insert
            columns = list(data.keys())
            placeholders = [f"${i+1}" for i in range(len(columns))]
            values = list(data.values())

            query = f"""
                INSERT INTO {self.table_name} ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
                RETURNING id, organization_id, name, description, filename, file_size,
                         mime_type, storage_path, current_version, status, created_by,
                         updated_by, metadata, tags, created_at, updated_at
            """

            logger.debug(f"Creating document: {query}")

            result = await self.db_manager.execute(query, values)
            row = result.result()[0]  # First (and only) row

            return self._row_to_model(row)

        except Exception as e:
            logger.error(f"Failed to create document: {e}")
            from doc_vault.exceptions import DatabaseError

            raise DatabaseError("Failed to create document") from e

    async def delete(self, id: UUID) -> bool:
        """
        Soft delete a document by setting status to 'deleted'.

        Args:
            id: Document UUID

        Returns:
            True if deleted, False if not found

        Raises:
            DatabaseError: If deletion fails
        """
        try:
            # Soft delete by updating status
            updates = {"status": "deleted"}
            updated_doc = await self.update(id, updates)
            return updated_doc is not None

        except Exception as e:
            logger.error(f"Failed to soft delete document {id}: {e}")
            from doc_vault.exceptions import DatabaseError

            raise DatabaseError("Failed to delete document") from e

    async def hard_delete(self, id: UUID) -> bool:
        """
        Permanently delete a document from the database.

        Args:
            id: Document UUID

        Returns:
            True if deleted, False if not found

        Raises:
            DatabaseError: If deletion fails
        """
        # Call the base class delete method for hard delete
        return await super().delete(id)

    async def list_by_prefix(
        self, org_id: UUID, prefix: str, limit: int = 100, offset: int = 0
    ) -> List[Document]:
        """
        List documents with a specific prefix (direct children only).

        v2.0 Feature: Hierarchical document organization via prefixes.

        Args:
            org_id: Organization UUID
            prefix: Prefix path (e.g., "/reports/2025/")
            limit: Maximum number of documents to return
            offset: Number of documents to skip

        Returns:
            List of Document instances matching the prefix

        Raises:
            DatabaseError: If query fails
        """
        try:
            org_id = self._ensure_uuid(org_id)

            # List documents with this exact prefix (direct children)
            # Exclude search_vector to avoid tsvector issues
            columns = [
                "id",
                "organization_id",
                "name",
                "description",
                "filename",
                "file_size",
                "mime_type",
                "storage_path",
                "prefix",
                "path",
                "current_version",
                "status",
                "created_by",
                "updated_by",
                "metadata",
                "tags",
                "created_at",
                "updated_at",
            ]

            query = f"""
                SELECT {', '.join(columns)} FROM {self.table_name}
                WHERE organization_id = $1 AND prefix = $2 AND status != 'deleted'
                ORDER BY name ASC
                LIMIT $3 OFFSET $4
            """

            result = await self.db_manager.execute(
                query, [org_id, prefix, limit, offset]
            )
            rows = result.result()

            return [self._row_to_model(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to list documents by prefix {prefix}: {e}")
            raise DatabaseError("Failed to list documents by prefix") from e

    async def list_recursive(
        self,
        org_id: UUID,
        prefix: str,
        max_depth: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Document]:
        """
        Recursively list documents under a prefix with optional depth limit.

        v2.0 Feature: Hierarchical document discovery with depth control.

        Args:
            org_id: Organization UUID
            prefix: Prefix path (e.g., "/reports/")
            max_depth: Maximum depth to traverse (None = unlimited)
                      Depth is calculated from prefix slashes
            limit: Maximum number of documents to return
            offset: Number of documents to skip

        Returns:
            List of Document instances under the prefix (recursively)

        Raises:
            DatabaseError: If query fails
        """
        try:
            org_id = self._ensure_uuid(org_id)

            # Calculate depth parameters if limit specified
            if max_depth is not None:
                # Count slashes in prefix to determine base depth
                base_depth = prefix.count("/") - 1  # -1 for leading slash
                max_allowed_depth = base_depth + max_depth
                # Create pattern for paths up to max depth
                # E.g., prefix="/reports/" with max_depth=2 allows:
                # /reports/*, /reports/*/*, but not /reports/*/*/*
                "/" * (max_allowed_depth + 1)

            # List all documents recursively under this prefix
            # Exclude search_vector to avoid tsvector issues
            columns = [
                "id",
                "organization_id",
                "name",
                "description",
                "filename",
                "file_size",
                "mime_type",
                "storage_path",
                "prefix",
                "path",
                "current_version",
                "status",
                "created_by",
                "updated_by",
                "metadata",
                "tags",
                "created_at",
                "updated_at",
            ]

            if max_depth is not None:
                # With depth limit: match paths starting with prefix and not exceeding depth
                query = f"""
                    SELECT {', '.join(columns)} FROM {self.table_name}
                    WHERE organization_id = $1
                      AND (prefix LIKE $2 || '%' OR path LIKE $2 || '%')
                      AND (prefix IS NULL OR (prefix NOT LIKE $2 || '%' || '/' || '%/%'))
                      AND status != 'deleted'
                    ORDER BY path ASC
                    LIMIT $3 OFFSET $4
                """
                result = await self.db_manager.execute(
                    query, [org_id, prefix, limit, offset]
                )
            else:
                # Without depth limit: all documents under prefix
                query = f"""
                    SELECT {', '.join(columns)} FROM {self.table_name}
                    WHERE organization_id = $1
                      AND (prefix LIKE $2 || '%' OR path LIKE $2 || '%')
                      AND status != 'deleted'
                    ORDER BY path ASC
                    LIMIT $3 OFFSET $4
                """
                result = await self.db_manager.execute(
                    query, [org_id, prefix, limit, offset]
                )

            rows = result.result()
            return [self._row_to_model(row) for row in rows]

        except Exception as e:
            logger.error(
                f"Failed to recursively list documents under prefix {prefix}: {e}"
            )
            raise DatabaseError("Failed to recursively list documents") from e

    @staticmethod
    def _calculate_depth(path: str) -> int:
        """
        Calculate depth of a path (number of slashes).

        Args:
            path: Path string (e.g., "/reports/2025/q1/")

        Returns:
            Number of levels in the path
        """
        if not path:
            return 0
        return path.count("/") - 1  # -1 for leading slash
