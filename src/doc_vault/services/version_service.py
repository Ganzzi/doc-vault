"""
Version service for DocVault.

Provides business logic for document versioning including listing versions,
restoring previous versions, and version management.
"""

import logging
from typing import List, Optional
from uuid import UUID

from doc_vault.database.postgres_manager import PostgreSQLManager
from doc_vault.database.repositories.acl import ACLRepository
from doc_vault.database.repositories.agent import AgentRepository
from doc_vault.database.repositories.document import DocumentRepository
from doc_vault.database.repositories.version import VersionRepository
from doc_vault.database.schemas.document import Document
from doc_vault.database.schemas.version import DocumentVersion, DocumentVersionCreate
from doc_vault.exceptions import (
    AgentNotFoundError,
    DocumentNotFoundError,
    PermissionDeniedError,
    ValidationError,
)

logger = logging.getLogger(__name__)


class VersionService:
    """
    Service for version management operations.

    Handles document versioning, version history, and version restoration.
    """

    def __init__(self, db_manager: PostgreSQLManager):
        """
        Initialize the VersionService.

        Args:
            db_manager: Database connection manager
        """
        self.db_manager = db_manager

        # Initialize repositories
        self.version_repo = VersionRepository(db_manager)
        self.document_repo = DocumentRepository(db_manager)
        self.acl_repo = ACLRepository(db_manager)
        self.agent_repo = AgentRepository(db_manager)

    async def _check_agent_exists(self, agent_id: UUID) -> None:
        """Check if an agent exists."""
        agent = await self.agent_repo.get_by_id(agent_id)
        if not agent:
            raise AgentNotFoundError(f"Agent {agent_id} not found")

    async def _check_document_exists(self, document_id: UUID) -> Document:
        """Check if a document exists and return it."""
        from doc_vault.database.schemas.document import Document

        document = await self.document_repo.get_by_id(document_id)
        if not document:
            raise DocumentNotFoundError(f"Document {document_id} not found")
        if document.status == "deleted":
            raise DocumentNotFoundError(f"Document {document_id} has been deleted")
        return document

    async def _check_permission(
        self, document_id: UUID, agent_id: UUID, permission: str
    ) -> None:
        """Check if an agent has permission for a document."""
        has_permission = await self.acl_repo.check_permission(
            document_id, agent_id, permission
        )
        if not has_permission:
            raise PermissionDeniedError(
                f"Agent {agent_id} does not have {permission} permission for document {document_id}"
            )

    async def list_versions(
        self,
        document_id: UUID,
        agent_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[DocumentVersion]:
        """
        List all versions of a document.

        Args:
            document_id: Document UUID
            agent_id: Agent UUID (requester)
            limit: Maximum number of versions to return
            offset: Number of versions to skip

        Returns:
            List of DocumentVersion instances ordered by version_number DESC

        Raises:
            DocumentNotFoundError: If document doesn't exist
            AgentNotFoundError: If agent doesn't exist
            PermissionDeniedError: If agent lacks READ permission
        """
        # Check agent exists
        await self._check_agent_exists(agent_id)

        # Check document exists
        await self._check_document_exists(document_id)

        # Check read permission
        await self._check_permission(document_id, agent_id, "READ")

        # Get versions
        versions = await self.version_repo.get_by_document(document_id, limit, offset)

        return versions

    async def restore_version(
        self,
        document_id: UUID,
        version_number: int,
        agent_id: UUID,
        change_description: str,
    ) -> DocumentVersion:
        """
        Restore a document to a previous version.

        This creates a new version that is a copy of the specified version.

        Args:
            document_id: Document UUID
            version_number: Version number to restore
            agent_id: Agent UUID (restorer)
            change_description: Description of the restoration

        Returns:
            New DocumentVersion instance representing the restored version

        Raises:
            DocumentNotFoundError: If document doesn't exist
            AgentNotFoundError: If agent doesn't exist
            PermissionDeniedError: If agent lacks WRITE permission
            ValidationError: If version doesn't exist
        """
        # Check agent exists
        await self._check_agent_exists(agent_id)

        # Check document exists
        document = await self._check_document_exists(document_id)

        # Check write permission
        await self._check_permission(document_id, agent_id, "WRITE")

        # Get the version to restore
        version_to_restore = await self.version_repo.get_by_document_and_version(
            document_id, version_number
        )
        if not version_to_restore:
            raise ValidationError(
                f"Version {version_number} not found for document {document_id}"
            )

        # Increment version number
        new_version_number = document.current_version + 1

        # Create new version record (copy of the old version)
        version_create = DocumentVersionCreate(
            document_id=document_id,
            version_number=new_version_number,
            filename=version_to_restore.filename,
            file_size=version_to_restore.file_size,
            storage_path=version_to_restore.storage_path,  # Same storage path
            mime_type=version_to_restore.mime_type,
            change_description=change_description,
            change_type="restore",
            created_by=agent_id,
            metadata=version_to_restore.metadata or {},
        )

        # Use transaction for atomicity
        async with self.db_manager.connection() as conn:
            async with conn.transaction():
                # Create the new version record
                new_version = await self.version_repo.create_from_create_schema(
                    version_create
                )

                # Update document to point to the restored version
                doc_updates = {
                    "current_version": new_version_number,
                    "filename": version_to_restore.filename,
                    "file_size": version_to_restore.file_size,
                    "storage_path": version_to_restore.storage_path,
                    "mime_type": version_to_restore.mime_type,
                    "updated_by": str(agent_id),
                }
                await self.document_repo.update(document_id, doc_updates)

        logger.info(
            f"Document {document_id} restored to version {version_number} "
            f"as new version {new_version_number} by agent {agent_id}"
        )
        return new_version

    async def get_version_info(
        self,
        document_id: UUID,
        version_number: int,
        agent_id: UUID,
    ) -> DocumentVersion:
        """
        Get information about a specific document version.

        Args:
            document_id: Document UUID
            version_number: Version number
            agent_id: Agent UUID (requester)

        Returns:
            DocumentVersion instance

        Raises:
            DocumentNotFoundError: If document doesn't exist
            AgentNotFoundError: If agent doesn't exist
            PermissionDeniedError: If agent lacks READ permission
            ValidationError: If version doesn't exist
        """
        # Check agent exists
        await self._check_agent_exists(agent_id)

        # Check document exists
        await self._check_document_exists(document_id)

        # Check read permission
        await self._check_permission(document_id, agent_id, "READ")

        # Get version info
        version = await self.version_repo.get_by_document_and_version(
            document_id, version_number
        )
        if not version:
            raise ValidationError(
                f"Version {version_number} not found for document {document_id}"
            )

        return version
