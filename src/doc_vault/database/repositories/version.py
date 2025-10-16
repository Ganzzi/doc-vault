"""
Version repository for DocVault.

Provides CRUD operations for document_versions table.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from doc_vault.database.postgres_manager import PostgreSQLManager
from doc_vault.database.repositories.base import BaseRepository
from doc_vault.database.schemas.version import DocumentVersion, DocumentVersionCreate
from doc_vault.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class VersionRepository(BaseRepository[DocumentVersion]):
    """
    Repository for DocumentVersion entities.

    Provides CRUD operations and version-specific queries.
    """

    @property
    def table_name(self) -> str:
        """Database table name."""
        return "document_versions"

    @property
    def model_class(self) -> type:
        """Pydantic model class for this repository."""
        return DocumentVersion

    def _row_to_model(self, row: Dict[str, Any]) -> DocumentVersion:
        """
        Convert database row dict to DocumentVersion model.

        Args:
            row: Database row as dict

        Returns:
            DocumentVersion instance
        """
        return DocumentVersion(
            id=row["id"],
            document_id=row["document_id"],
            version_number=row["version_number"],
            filename=row["filename"],
            file_size=row["file_size"],
            storage_path=row["storage_path"],
            mime_type=row["mime_type"],
            change_description=row["change_description"],
            change_type=row["change_type"],
            created_by=row["created_by"],
            metadata=row["metadata"] or {},
            created_at=row["created_at"],
        )

    def _model_to_dict(self, model: DocumentVersion) -> Dict[str, Any]:
        """
        Convert DocumentVersion model to database dict.

        Args:
            model: DocumentVersion instance

        Returns:
            Dict suitable for database insertion/update
        """
        data = {
            "document_id": model.document_id,
            "version_number": model.version_number,
            "filename": model.filename,
            "file_size": model.file_size,
            "storage_path": model.storage_path,
            "mime_type": model.mime_type,
            "change_description": model.change_description,
            "change_type": model.change_type,
            "created_by": model.created_by,
            "metadata": model.metadata,
        }

        # Include ID if it exists (for updates)
        if hasattr(model, "id") and model.id:
            data["id"] = model.id

        return data

    async def get_by_document(
        self, document_id: UUID, limit: int = 100, offset: int = 0
    ) -> List[DocumentVersion]:
        """
        Get all versions for a document.

        Args:
            document_id: Document UUID
            limit: Maximum number of versions to return
            offset: Number of versions to skip

        Returns:
            List of DocumentVersion instances ordered by version_number ASC
        """
        try:
            query = """
                SELECT * FROM document_versions
                WHERE document_id = $1
                ORDER BY version_number ASC
                LIMIT $2 OFFSET $3
            """
            result = await self.db_manager.execute(query, [document_id, limit, offset])
            rows = result.result()
            return [self._row_to_model(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get versions for document {document_id}: {e}")
            from doc_vault.exceptions import DatabaseError

            raise DatabaseError("Failed to get document versions") from e

    async def get_by_document_and_version(
        self, document_id: UUID, version_number: int
    ) -> Optional[DocumentVersion]:
        """
        Get a specific version of a document.

        Args:
            document_id: Document UUID
            version_number: Version number

        Returns:
            DocumentVersion instance or None if not found
        """
        try:
            query = """
                SELECT * FROM document_versions
                WHERE document_id = $1 AND version_number = $2
            """
            result = await self.db_manager.execute(query, [document_id, version_number])
            rows = result.result()
            if not rows:
                return None
            return self._row_to_model(rows[0])

        except Exception as e:
            logger.error(
                f"Failed to get version {version_number} for document {document_id}: {e}"
            )
            from doc_vault.exceptions import DatabaseError

            raise DatabaseError("Failed to get document version") from e

    async def get_latest_version(self, document_id: UUID) -> Optional[DocumentVersion]:
        """
        Get the latest version for a document.

        Args:
            document_id: Document UUID

        Returns:
            Latest DocumentVersion instance or None if no versions exist
        """
        try:
            query = """
                SELECT * FROM document_versions
                WHERE document_id = $1
                ORDER BY version_number DESC
                LIMIT 1
            """
            result = await self.db_manager.execute(query, [document_id])
            rows = result.result()
            if not rows:
                return None
            return self._row_to_model(rows[0])

        except Exception as e:
            logger.error(
                f"Failed to get latest version for document {document_id}: {e}"
            )
            from doc_vault.exceptions import DatabaseError

            raise DatabaseError("Failed to get latest document version") from e

    async def get_version_count(self, document_id: UUID) -> int:
        """
        Get the total number of versions for a document.

        Args:
            document_id: Document UUID

        Returns:
            Number of versions
        """
        try:
            query = """
                SELECT COUNT(*) as count FROM document_versions
                WHERE document_id = $1
            """
            result = await self.db_manager.execute(query, [document_id])
            return result.result()[0]["count"]

        except Exception as e:
            logger.error(f"Failed to count versions for document {document_id}: {e}")
            from doc_vault.exceptions import DatabaseError

            raise DatabaseError("Failed to count document versions") from e

    async def create_initial_version(
        self,
        document_id: UUID,
        filename: str,
        file_size: int,
        storage_path: str,
        mime_type: Optional[str],
        created_by: UUID,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DocumentVersion:
        """
        Create the initial version (version 1) for a new document.

        Args:
            document_id: Document UUID
            filename: Original filename
            file_size: File size in bytes
            storage_path: Storage path
            mime_type: MIME type
            created_by: Agent who created the version
            metadata: Optional version metadata

        Returns:
            Created DocumentVersion instance
        """
        try:
            version_data = DocumentVersionCreate(
                document_id=document_id,
                version_number=1,
                filename=filename,
                file_size=file_size,
                storage_path=storage_path,
                mime_type=mime_type,
                change_description="Initial version",
                change_type="create",
                created_by=created_by,
                metadata=metadata or {},
            )
            return await self.create_from_create_schema(version_data)

        except Exception as e:
            logger.error(
                f"Failed to create initial version for document {document_id}: {e}"
            )
            from doc_vault.exceptions import DatabaseError

            raise DatabaseError("Failed to create initial document version") from e

    async def create_new_version(
        self,
        document_id: UUID,
        version_number: int,
        filename: str,
        file_size: int,
        storage_path: str,
        mime_type: Optional[str],
        created_by: UUID,
        change_description: Optional[str] = None,
        change_type: str = "update",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DocumentVersion:
        """
        Create a new version for an existing document.

        Args:
            document_id: Document UUID
            version_number: New version number
            filename: Version filename
            file_size: File size in bytes
            storage_path: Storage path
            mime_type: MIME type
            created_by: Agent who created the version
            change_description: Description of changes
            change_type: Type of change ('create', 'update', 'restore')
            metadata: Optional version metadata

        Returns:
            Created DocumentVersion instance
        """
        try:
            version_data = DocumentVersionCreate(
                document_id=document_id,
                version_number=version_number,
                filename=filename,
                file_size=file_size,
                storage_path=storage_path,
                mime_type=mime_type,
                change_description=change_description,
                change_type=change_type,
                created_by=created_by,
                metadata=metadata or {},
            )
            return await self.create_from_create_schema(version_data)

        except Exception as e:
            logger.error(
                f"Failed to create version {version_number} for document {document_id}: {e}"
            )
            from doc_vault.exceptions import DatabaseError

            raise DatabaseError("Failed to create document version") from e

    async def create_from_create_schema(
        self, create_data: DocumentVersionCreate
    ) -> DocumentVersion:
        """
        Create a document version from DocumentVersionCreate schema.

        This is a convenience method that handles the conversion from
        create schema to full model.

        Args:
            create_data: DocumentVersionCreate schema instance

        Returns:
            Created DocumentVersion instance
        """
        # Convert create schema to dict and create model
        model_data = create_data.model_dump()
        # Add created_at timestamp
        from datetime import datetime

        model_data["created_at"] = datetime.now()
        # Create a temporary model instance for the base class create method
        temp_model = DocumentVersion(**model_data)
        return await self.create(temp_model)

    async def update(
        self, id: UUID, updates: Dict[str, Any]
    ) -> Optional[DocumentVersion]:
        """
        Update a document version by ID.

        Note: Document versions don't have updated_at column, so we don't set it.

        Args:
            id: Version UUID
            updates: Dict of field updates

        Returns:
            Updated DocumentVersion instance or None if not found

        Raises:
            DatabaseError: If update fails
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

            query = f"""
                UPDATE {self.table_name}
                SET {', '.join(set_parts)}
                WHERE id = ${param_index}
                RETURNING *
            """

            logger.debug(f"Updating {self.model_class.__name__} {id}: {query}")

            result = await self.db_manager.execute(query, values)
            rows = result.result()

            if not rows:
                return None

            return self._row_to_model(rows[0])

        except Exception as e:
            logger.error(f"Failed to update {self.model_class.__name__} {id}: {e}")
            raise DatabaseError(f"Failed to update {self.model_class.__name__}") from e
