"""
Core DocVault SDK implementation.

This module contains the main DocVaultSDK class that provides
the high-level API for document management.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from .config import Config
from .database.postgres_manager import PostgreSQLManager
from .database.repositories.agent import AgentRepository
from .database.repositories.organization import OrganizationRepository
from .database.schemas.agent import AgentCreate
from .database.schemas.organization import OrganizationCreate
from .exceptions import AgentNotFoundError, OrganizationNotFoundError
from .services.access_service import AccessService
from .services.document_service import DocumentService
from .services.version_service import VersionService
from .storage.s3_client import S3StorageBackend

logger = logging.getLogger(__name__)


class DocVaultSDK:
    """
    Main DocVault SDK class for document management.

    This class provides the high-level API for uploading, downloading,
    and managing documents with role-based access control.
    """

    def __init__(self, config: Optional[Config] = None) -> None:
        """
        Initialize the DocVault SDK.

        Args:
            config: Configuration object. If None, loads from environment.
        """
        self.config = config or Config.from_env()
        self._db_manager: Optional[PostgreSQLManager] = None
        self._storage_backend: Optional[S3StorageBackend] = None
        self._document_service: Optional[DocumentService] = None
        self._access_service: Optional[AccessService] = None
        self._version_service: Optional[VersionService] = None
        self._initialized = False

    async def __aenter__(self) -> "DocVaultSDK":
        """Async context manager entry."""
        if self._initialized:
            return self

        # Initialize database manager
        self._db_manager = PostgreSQLManager(self.config)
        await self._db_manager.initialize()

        # Initialize storage backend
        self._storage_backend = S3StorageBackend(
            endpoint=self.config.minio.endpoint,
            access_key=self.config.minio.access_key,
            secret_key=self.config.minio.secret_key,
            secure=self.config.minio.secure,
        )

        # Initialize services
        self._document_service = DocumentService(
            db_manager=self._db_manager,
            storage_backend=self._storage_backend,
            bucket_prefix=self.config.docvault.bucket_prefix,
        )
        self._access_service = AccessService(
            db_manager=self._db_manager,
        )
        self._version_service = VersionService(
            db_manager=self._db_manager,
        )

        self._initialized = True
        logger.info("DocVault SDK initialized successfully")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._db_manager:
            await self._db_manager.close()
            self._db_manager = None

        # Reset all services and state
        self._storage_backend = None
        self._document_service = None
        self._access_service = None
        self._version_service = None
        self._initialized = False
        logger.info("DocVault SDK cleaned up successfully")

    async def _resolve_external_ids(
        self, organization_id: Optional[str] = None, agent_id: Optional[str] = None
    ) -> tuple[Optional[UUID], Optional[UUID]]:
        """Resolve external IDs to UUIDs."""
        org_uuid = None
        agent_uuid = None

        if organization_id:
            org_repo = OrganizationRepository(self._db_manager)
            organization = await org_repo.get_by_external_id(organization_id)
            if not organization:
                raise OrganizationNotFoundError(
                    f"Organization {organization_id} not found"
                )
            org_uuid = organization.id

        if agent_id:
            agent_repo = AgentRepository(self._db_manager)
            agent = await agent_repo.get_by_external_id(agent_id)
            if not agent:
                raise AgentNotFoundError(f"Agent {agent_id} not found")
            agent_uuid = agent.id

        return org_uuid, agent_uuid

        self._storage_backend = None
        self._document_service = None
        self._access_service = None
        self._version_service = None
        self._initialized = False
        logger.info("DocVault SDK shut down successfully")

    def __str__(self) -> str:
        """String representation."""
        return f"DocVaultSDK(config={self.config})"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return self.__str__()

    # Document Operations

    async def upload(
        self,
        file_path: str,
        name: str,
        organization_id: str,
        agent_id: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Upload a document.

        Args:
            file_path: Path to the file to upload
            name: Display name for the document
            organization_id: Organization external ID
            agent_id: Agent external ID (uploader)
            description: Optional description
            tags: Optional list of tags
            metadata: Optional custom metadata

        Returns:
            Document: The created document
        """
        if not self._document_service:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )

        # Resolve external IDs to UUIDs
        org_uuid, agent_uuid = await self._resolve_external_ids(
            organization_id=organization_id, agent_id=agent_id
        )

        return await self._document_service.upload_document(
            file_path=file_path,
            name=name,
            organization_id=org_uuid,
            agent_id=agent_uuid,
            description=description,
            tags=tags or [],
            metadata=metadata or {},
        )

    async def download(
        self,
        document_id: UUID,
        agent_id: str,
        version: Optional[int] = None,
    ) -> bytes:
        """
        Download a document.

        Args:
            document_id: Document UUID
            agent_id: Agent external ID (requester)
            version: Optional version number (None = current)

        Returns:
            bytes: The document content
        """
        if not self._document_service:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )
        # Resolve external IDs to UUIDs
        _, agent_uuid = await self._resolve_external_ids(agent_id=agent_id)

        return await self._document_service.download_document(
            document_id=document_id,
            agent_id=agent_uuid,
            version=version,
        )

    async def update_metadata(
        self,
        document_id: UUID,
        agent_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Update document metadata.

        Args:
            document_id: Document UUID
            agent_id: Agent external ID (updater)
            name: Optional new name
            description: Optional new description
            tags: Optional new tags
            metadata: Optional new metadata

        Returns:
            Document: Updated document
        """
        if not self._document_service:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )
        # Resolve external IDs to UUIDs
        _, agent_uuid = await self._resolve_external_ids(agent_id=agent_id)

        return await self._document_service.update_metadata(
            document_id=document_id,
            agent_id=agent_uuid,
            name=name,
            description=description,
            tags=tags,
            metadata=metadata,
        )

    async def replace(
        self,
        document_id: UUID,
        file_path: str,
        agent_id: str,
        change_description: str,
    ):
        """
        Replace document content (creates new version).

        Args:
            document_id: Document UUID
            file_path: Path to new file content
            agent_id: Agent external ID (updater)
            change_description: Description of the change

        Returns:
            DocumentVersion: The new version
        """
        if not self._document_service:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )
        # Resolve external IDs to UUIDs
        _, agent_uuid = await self._resolve_external_ids(agent_id=agent_id)

        return await self._document_service.replace_document(
            document_id=document_id,
            file_path=file_path,
            agent_id=agent_uuid,
            change_description=change_description,
        )

    async def delete(
        self,
        document_id: UUID,
        agent_id: str,
        hard_delete: bool = False,
    ) -> None:
        """
        Delete a document.

        Args:
            document_id: Document UUID
            agent_id: Agent external ID (deleter)
            hard_delete: If True, permanently delete; if False, soft delete
        """
        if not self._document_service:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )
        # Resolve external IDs to UUIDs
        _, agent_uuid = await self._resolve_external_ids(agent_id=agent_id)

        await self._document_service.delete_document(
            document_id=document_id,
            agent_id=agent_uuid,
            hard_delete=hard_delete,
        )

    async def list_documents(
        self,
        organization_id: str,
        agent_id: str,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0,
    ):
        """
        List documents accessible to an agent.

        Args:
            organization_id: Organization external ID
            agent_id: Agent external ID (requester)
            status: Optional status filter ('active', 'draft', 'archived', 'deleted')
            tags: Optional tag filters
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List[Document]: Accessible documents
        """
        if not self._document_service:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )
        # Resolve external IDs to UUIDs
        org_uuid, agent_uuid = await self._resolve_external_ids(
            organization_id=organization_id, agent_id=agent_id
        )

        return await self._document_service.list_documents(
            organization_id=org_uuid,
            agent_id=agent_uuid,
            status=status,
            tags=tags,
            limit=limit,
            offset=offset,
        )

    async def search(
        self,
        query: str,
        organization_id: str,
        agent_id: str,
        limit: int = 20,
    ):
        """
        Search documents by text query.

        Args:
            query: Search query
            organization_id: Organization external ID
            agent_id: Agent external ID (requester)
            limit: Maximum number of results

        Returns:
            List[Document]: Matching documents
        """
        # Resolve external IDs to UUIDs
        org_uuid, agent_uuid = await self._resolve_external_ids(
            organization_id=organization_id, agent_id=agent_id
        )

        return await self._document_service.search_documents(
            query=query,
            organization_id=org_uuid,
            agent_id=agent_uuid,
            limit=limit,
        )

    # Access Control

    async def share(
        self,
        document_id: UUID,
        agent_id: str,
        permission: str,
        granted_by: str,
        expires_at=None,
    ) -> None:
        """
        Share a document with another agent.

        Args:
            document_id: Document UUID
            agent_id: Agent external ID to grant access to
            permission: Permission level ('READ', 'WRITE', 'DELETE', 'SHARE', 'ADMIN')
            granted_by: Agent external ID granting access
            expires_at: Optional expiration datetime
        """
        if not self._access_service:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )
        # Resolve external IDs to UUIDs
        _, agent_uuid = await self._resolve_external_ids(agent_id=agent_id)
        _, granted_by_uuid = await self._resolve_external_ids(agent_id=granted_by)

        await self._access_service.grant_access(
            document_id=document_id,
            agent_id=agent_uuid,
            permission=permission,
            granted_by=granted_by_uuid,
            expires_at=expires_at,
        )

    async def revoke(
        self,
        document_id: UUID,
        agent_id: str,
        permission: str,
        revoked_by: str,
    ) -> None:
        """
        Revoke access to a document.

        Args:
            document_id: Document UUID
            agent_id: Agent external ID to revoke access from
            permission: Permission to revoke
            revoked_by: Agent external ID revoking access
        """
        if not self._access_service:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )
        # Resolve external IDs to UUIDs
        _, agent_uuid = await self._resolve_external_ids(agent_id=agent_id)
        _, revoked_by_uuid = await self._resolve_external_ids(agent_id=revoked_by)

        await self._access_service.revoke_access(
            document_id=document_id,
            agent_id=agent_uuid,
            permission=permission,
            revoked_by=revoked_by_uuid,
        )

    async def check_permission(
        self,
        document_id: UUID,
        agent_id: str,
        permission: str,
    ) -> bool:
        """
        Check if an agent has a specific permission on a document.

        Args:
            document_id: Document UUID
            agent_id: Agent external ID
            permission: Permission to check

        Returns:
            bool: True if agent has permission
        """
        if not self._access_service:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )
        # Resolve external IDs to UUIDs
        _, agent_uuid = await self._resolve_external_ids(agent_id=agent_id)

        return await self._access_service.check_permission(
            document_id=document_id,
            agent_id=agent_uuid,
            permission=permission,
        )

    async def list_accessible_documents(
        self,
        agent_id: str,
        organization_id: str,
        permission: Optional[str] = None,
    ):
        """
        List documents accessible to an agent.

        Args:
            agent_id: Agent external ID
            organization_id: Organization external ID
            permission: Optional permission filter

        Returns:
            List[Document]: Accessible documents
        """
        if not self._access_service:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )
        # Resolve external IDs to UUIDs
        org_uuid, agent_uuid = await self._resolve_external_ids(
            organization_id=organization_id, agent_id=agent_id
        )

        return await self._access_service.list_accessible_documents(
            agent_id=agent_uuid,
            organization_id=org_uuid,
            permission=permission,
        )

    async def get_document_permissions(
        self,
        document_id: UUID,
        agent_id: str,
    ):
        """
        Get all permissions for a document.

        Args:
            document_id: Document UUID
            agent_id: Agent external ID (must have ADMIN permission)

        Returns:
            List[ACL]: Document permissions
        """
        if not self._access_service:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )
        # Resolve external IDs to UUIDs
        _, agent_uuid = await self._resolve_external_ids(agent_id=agent_id)

        return await self._access_service.get_document_permissions(
            document_id=document_id,
            agent_id=agent_uuid,
        )

    # Version Management

    async def get_versions(
        self,
        document_id: UUID,
        agent_id: str,
    ):
        """
        Get all versions of a document.

        Args:
            document_id: Document UUID
            agent_id: Agent external ID (requester)

        Returns:
            List[DocumentVersion]: Document versions
        """
        if not self._version_service:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )
        # Resolve external IDs to UUIDs
        _, agent_uuid = await self._resolve_external_ids(agent_id=agent_id)

        return await self._version_service.list_versions(
            document_id=document_id,
            agent_id=agent_uuid,
        )

    async def restore_version(
        self,
        document_id: UUID,
        version_number: int,
        agent_id: str,
        change_description: str,
    ):
        """
        Restore a previous version (creates new version).

        Args:
            document_id: Document UUID
            version_number: Version to restore
            agent_id: Agent external ID (restorer)
            change_description: Description of the restore

        Returns:
            DocumentVersion: New version created from restore
        """
        if not self._version_service:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )
        # Resolve external IDs to UUIDs
        _, agent_uuid = await self._resolve_external_ids(agent_id=agent_id)

        return await self._version_service.restore_version(
            document_id=document_id,
            version_number=version_number,
            agent_id=agent_uuid,
            change_description=change_description,
        )

    async def get_version_info(
        self,
        document_id: UUID,
        version_number: int,
        agent_id: str,
    ):
        """
        Get information about a specific version.

        Args:
            document_id: Document UUID
            version_number: Version number
            agent_id: Agent external ID (requester)

        Returns:
            DocumentVersion: Version information
        """
        if not self._version_service:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )
        # Resolve external IDs to UUIDs
        _, agent_uuid = await self._resolve_external_ids(agent_id=agent_id)

        return await self._version_service.get_version_info(
            document_id=document_id,
            version_number=version_number,
            agent_id=agent_uuid,
        )

    # Organization & Agent Management

    async def register_organization(
        self,
        external_id: str,
        name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Register a new organization (idempotent).

        Args:
            external_id: External organization ID
            name: Organization name
            metadata: Optional custom metadata

        Returns:
            Organization: The organization
        """
        if not self._db_manager:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )

        org_repo = OrganizationRepository(self._db_manager)

        # Check if organization already exists
        existing = await org_repo.get_by_external_id(external_id)
        if existing:
            return existing

        # Create new organization
        org_create = OrganizationCreate(
            external_id=external_id,
            name=name,
            metadata=metadata or {},
        )

        return await org_repo.create_from_create_schema(org_create)

    async def register_agent(
        self,
        external_id: str,
        organization_id: str,
        name: str,
        email: Optional[str] = None,
        agent_type: str = "human",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Register a new agent (idempotent).

        Args:
            external_id: External agent ID
            organization_id: Organization external ID
            name: Agent name
            email: Optional email
            agent_type: 'human', 'ai', or 'service'
            metadata: Optional custom metadata

        Returns:
            Agent: The agent
        """
        if not self._db_manager:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )

        # First get the organization to get its UUID
        org_repo = OrganizationRepository(self._db_manager)
        org = await org_repo.get_by_external_id(organization_id)
        if not org:
            raise ValueError(
                f"Organization with external_id '{organization_id}' not found"
            )

        agent_repo = AgentRepository(self._db_manager)

        # Check if agent already exists
        existing = await agent_repo.get_by_external_id(external_id)
        if existing:
            return existing

        # Create new agent
        agent_create = AgentCreate(
            external_id=external_id,
            organization_id=str(org.id),
            name=name,
            email=email,
            agent_type=agent_type,
            metadata=metadata or {},
        )

        return await agent_repo.create_from_create_schema(agent_create)

    async def get_organization(self, external_id: str):
        """
        Get organization by external ID.

        Args:
            external_id: Organization external ID

        Returns:
            Organization: The organization
        """
        if not self._db_manager:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )

        org_repo = OrganizationRepository(self._db_manager)
        org = await org_repo.get_by_external_id(external_id)
        if not org:
            raise ValueError(f"Organization with external_id '{external_id}' not found")
        return org

    async def get_agent(self, external_id: str):
        """
        Get agent by external ID.

        Args:
            external_id: Agent external ID

        Returns:
            Agent: The agent
        """
        if not self._db_manager:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )

        agent_repo = AgentRepository(self._db_manager)
        agent = await agent_repo.get_by_external_id(external_id)
        if not agent:
            raise ValueError(f"Agent with external_id '{external_id}' not found")
        return agent
