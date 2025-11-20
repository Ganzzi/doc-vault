"""
Core DocVault SDK implementation.

This module contains the main DocVaultSDK class that provides
the high-level API for document management.
"""

import logging
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional
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
            endpoint=self.config.minio_endpoint,
            access_key=self.config.minio_access_key,
            secret_key=self.config.minio_secret_key,
            secure=self.config.minio_secure,
        )

        # Initialize services
        self._document_service = DocumentService(
            db_manager=self._db_manager,
            storage_backend=self._storage_backend,
            bucket_prefix=self.config.bucket_prefix,
        )
        self._access_service = AccessService(
            db_manager=self._db_manager,
        )
        self._version_service = VersionService(
            db_manager=self._db_manager,
        )

        # Initialize organization and agent services (v2.0)
        from doc_vault.services.organization_service import OrganizationService
        from doc_vault.services.agent_service import AgentService

        self._organization_service = OrganizationService(
            db_manager=self._db_manager,
        )
        self._agent_service = AgentService(
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
        self._organization_service = None
        self._agent_service = None
        self._initialized = False
        logger.info("DocVault SDK cleaned up successfully")

    async def _resolve_external_ids(
        self, organization_id: Optional[str] = None, agent_id: Optional[str] = None
    ) -> tuple[Optional[UUID], Optional[UUID]]:
        """
        Resolve external IDs to UUIDs.

        In v2.0, external_id IS the UUID, so this just ensures proper UUID format.
        """
        org_uuid = None
        agent_uuid = None

        if organization_id:
            # In v2.0, organization_id IS the UUID
            if isinstance(organization_id, str):
                org_uuid = UUID(organization_id)
            else:
                org_uuid = organization_id

        if agent_id:
            # In v2.0, agent_id IS the UUID
            if isinstance(agent_id, str):
                agent_uuid = UUID(agent_id)
            else:
                agent_uuid = agent_id

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
        file_input: str | bytes | BinaryIO,
        name: str,
        organization_id: str | UUID,
        agent_id: str | UUID,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        content_type: Optional[str] = None,
        filename: Optional[str] = None,
        prefix: Optional[str] = None,
    ):
        """
        Upload a document with flexible input support.

        Supports file paths (str), bytes, and binary streams (BinaryIO).

        Args:
            file_input: File path (str), bytes, or binary stream
            name: Document display name
            organization_id: Organization UUID or string
            agent_id: Agent UUID or string
            description: Optional description
            tags: Optional tags list
            metadata: Optional custom metadata dict
            content_type: Optional MIME type override
            filename: Optional filename override
            prefix: Optional hierarchical prefix (e.g., '/reports/2025/')

        Returns:
            Document: The created document instance
        """
        if not self._document_service:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )

        return await self._document_service.upload_enhanced(
            file_input=file_input,
            name=name,
            organization_id=organization_id,
            agent_id=agent_id,
            description=description,
            tags=tags,
            metadata=metadata,
            content_type=content_type,
            filename=filename,
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
        document_id: str | UUID,
        file_input: str | bytes | BinaryIO,
        agent_id: str | UUID,
        change_description: str = "Content updated",
        create_version: bool = True,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
    ):
        """
        Replace document content with flexible input support.

        Args:
            document_id: Document UUID or string
            file_input: File path (str), bytes, or binary stream
            agent_id: Agent UUID or string
            change_description: Description of the change (default: "Content updated")
            create_version: Whether to create version before replacement (default: True)
            filename: Optional filename override
            content_type: Optional MIME type override

        Returns:
            Document: The updated document instance
        """
        if not self._document_service:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )

        return await self._document_service.replace_document_content(
            document_id=document_id,
            file_input=file_input,
            agent_id=agent_id,
            change_description=change_description,
            create_version=create_version,
            filename=filename,
            content_type=content_type,
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

    async def list_docs(
        self,
        organization_id: str | UUID,
        agent_id: str | UUID,
        prefix: Optional[str] = None,
        recursive: bool = False,
        max_depth: Optional[int] = None,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Dict[str, Any]:
        """
        List documents with hierarchical organization support.

        Args:
            organization_id: Organization UUID or string
            agent_id: Agent UUID or string
            prefix: Optional hierarchical prefix filter (e.g., '/reports/2025/')
            recursive: If True, list recursively under prefix
            max_depth: Maximum recursion depth (None = unlimited)
            status: Optional status filter ('active', 'draft', 'archived', 'deleted')
            tags: Optional tag filters
            limit: Maximum number of results per page
            offset: Pagination offset
            sort_by: Sort field (default: 'created_at')
            sort_order: Sort direction ('asc' or 'desc')

        Returns:
            Dictionary with documents list and pagination metadata
        """
        if not self._document_service:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )

        return await self._document_service.list_documents_paginated(
            organization_id=organization_id,
            agent_id=agent_id,
            status=status,
            tags=tags,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    async def search(
        self,
        query: str,
        organization_id: str | UUID,
        agent_id: str | UUID,
        prefix: Optional[str] = None,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Search documents with optional filters.

        Args:
            query: Search query text
            organization_id: Organization UUID or string
            agent_id: Agent UUID or string
            prefix: Optional hierarchical prefix filter (e.g., '/reports/')
            status: Optional status filter
            tags: Optional tag filter
            limit: Maximum results
            offset: Result offset for pagination

        Returns:
            Dictionary with search results and metadata
        """
        if not self._document_service:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )

        return await self._document_service.search_documents_enhanced(
            query=query,
            organization_id=organization_id,
            agent_id=agent_id,
            prefix=prefix,
            status=status,
            tags=tags,
            limit=limit,
            offset=offset,
        )

    # Access Control & Permissions

    async def get_permissions(
        self,
        document_id: str | UUID,
        agent_id: Optional[str | UUID] = None,
        org_id: Optional[str | UUID] = None,
    ) -> Dict[str, Any]:
        """
        Get permissions for a document.

        Returns all permissions if agent_id is None, or permissions for specific agent.

        Args:
            document_id: Document UUID or string
            agent_id: Optional agent UUID/string to filter permissions
            org_id: Optional organization UUID/string for validation

        Returns:
            Dictionary with permission details
        """
        if not self._access_service:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )

        return await self._access_service.get_permissions_detailed(
            document_id=document_id,
            agent_id=agent_id,
        )

    async def set_permissions(
        self,
        document_id: str | UUID,
        permissions: List[dict],
        granted_by: str | UUID,
    ) -> List[Any]:
        """
        Set permissions for a document in bulk.

        Replaces existing permissions with the provided list.

        Args:
            document_id: Document UUID or string
            permissions: List of permission dictionaries with keys:
                - agent_id: UUID or string
                - permission: Permission level (READ, WRITE, DELETE, SHARE, ADMIN)
                - expires_at: Optional expiration datetime
            granted_by: UUID or string of agent granting permissions

        Returns:
            List of created ACL instances

        Example:
            ```python
            await vault.set_permissions(
                document_id=doc_id,
                permissions=[
                    {"agent_id": agent1, "permission": "READ"},
                    {"agent_id": agent2, "permission": "WRITE", "expires_at": datetime(2026, 1, 1)},
                ],
                granted_by=admin_id
            )
            ```
        """
        if not self._access_service:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )

        return await self._access_service.set_permissions_bulk(
            document_id=document_id,
            permissions=permissions,
            granted_by=granted_by,
        )

    # Version Management

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

    # Organization & Agent Management

    async def register_organization(
        self,
        external_id: str,
        name: str = None,  # v1.0 compatibility - ignored in v2.0
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Register a new organization (v2.0 compatible).

        In v2.0, external_id is used as the UUID for the organization.
        The 'name' parameter is kept for v1.0 compatibility but is ignored.

        Args:
            external_id: External organization UUID (string)
            name: Deprecated in v2.0 (kept for compatibility)
            metadata: Optional custom metadata

        Returns:
            Organization: The organization
        """
        if not self._organization_service:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )

        # Use v2.0 service
        return await self._organization_service.register_organization(
            org_id=external_id,
            metadata=metadata or {},
        )

    async def register_agent(
        self,
        external_id: str,
        organization_id: str,
        name: str = None,  # v1.0 compatibility - ignored in v2.0
        email: Optional[str] = None,  # v1.0 compatibility - ignored in v2.0
        agent_type: str = "human",  # v1.0 compatibility - ignored in v2.0
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Register a new agent (v2.0 compatible).

        In v2.0, external_id is used as the UUID for the agent.
        The 'name', 'email', and 'agent_type' parameters are kept for
        v1.0 compatibility but are ignored.

        Args:
            external_id: External agent UUID (string)
            organization_id: Organization UUID (string)
            name: Deprecated in v2.0 (kept for compatibility)
            email: Deprecated in v2.0 (kept for compatibility)
            agent_type: Deprecated in v2.0 (kept for compatibility)
            metadata: Optional custom metadata

        Returns:
            Agent: The agent
        """
        if not self._agent_service:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )

        # Use v2.0 service
        return await self._agent_service.register_agent(
            agent_id=external_id,
            organization_id=organization_id,
            metadata=metadata or {},
        )

    async def get_organization(self, external_id: str):
        """
        Get organization by external ID.

        Args:
            external_id: Organization UUID (string)

        Returns:
            Organization: The organization
        """
        if not self._db_manager:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )

        # In v2.0, external_id IS the organization id (UUID)
        org_repo = OrganizationRepository(self._db_manager)
        org_uuid = UUID(external_id) if isinstance(external_id, str) else external_id
        org = await org_repo.get_by_id(org_uuid)
        if not org:
            raise ValueError(f"Organization with ID '{external_id}' not found")
        return org

    async def get_agent(self, external_id: str):
        """
        Get agent by external ID (v2.0: the UUID itself).

        Args:
            external_id: Agent UUID (string)

        Returns:
            Agent: The agent
        """
        if not self._db_manager:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )

        # In v2.0, external_id IS the agent id (UUID)
        agent_repo = AgentRepository(self._db_manager)
        agent_uuid = UUID(external_id) if isinstance(external_id, str) else external_id
        agent = await agent_repo.get_by_id(agent_uuid)
        if not agent:
            raise ValueError(f"Agent with ID '{external_id}' not found")
        return agent

    async def delete_organization(
        self,
        org_id: UUID | str,
        force: bool = False,
    ) -> None:
        """
        Delete an organization.

        Args:
            org_id: Organization UUID or string
            force: If True, force delete even if organization has documents (default: False)

        Raises:
            RuntimeError: If SDK not initialized
            OrganizationNotFoundError: If organization doesn't exist
            ValidationError: If organization has active documents and force=False
        """
        if not self._organization_service:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )

        org_uuid = UUID(org_id) if isinstance(org_id, str) else org_id
        await self._organization_service.delete_organization(
            org_id=org_uuid,
            force=force,
        )

    async def remove_agent(
        self,
        agent_id: UUID | str,
        force: bool = False,
    ) -> None:
        """
        Remove an agent from the system.

        Args:
            agent_id: Agent UUID or string
            force: If True, force delete even if agent has created documents (default: False)

        Raises:
            RuntimeError: If SDK not initialized
            AgentNotFoundError: If agent doesn't exist
            ValidationError: If agent has active documents and force=False
        """
        if not self._agent_service:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )

        agent_uuid = UUID(agent_id) if isinstance(agent_id, str) else agent_id
        await self._agent_service.remove_agent(
            agent_id=agent_uuid,
            force=force,
        )

    # ==========================================================================
    # Additional v2.0 Methods
    # ==========================================================================

    async def get_document_details(
        self,
        document_id: str | UUID,
        agent_id: str | UUID,
        include_versions: bool = True,
        include_permissions: bool = False,
    ) -> Dict[str, Any]:
        """
        Get comprehensive document details with version and permission info.

        Args:
            document_id: Document UUID or string
            agent_id: Agent UUID or string
            include_versions: Include version history (default: True)
            include_permissions: Include permission details (default: False)

        Returns:
            Dictionary with document details, versions, and optionally permissions
        """
        if not self._document_service:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )

        return await self._document_service.get_document_details(
            document_id=document_id,
            agent_id=agent_id,
            include_versions=include_versions,
            include_permissions=include_permissions,
        )

    async def transfer_ownership(
        self,
        document_id: str | UUID,
        new_owner_id: str | UUID,
        transferred_by: str | UUID,
    ):
        """
        Transfer document ownership to another agent.

        Args:
            document_id: Document UUID or string
            new_owner_id: New owner agent UUID or string
            transferred_by: Transferring agent UUID or string (must be current owner)

        Returns:
            Updated Document instance
        """
        if not self._access_service:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )

        return await self._access_service.transfer_ownership(
            document_id=document_id,
            new_owner_id=new_owner_id,
            transferred_by=transferred_by,
        )
