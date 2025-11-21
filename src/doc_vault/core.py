"""
Core DocVault SDK implementation.

This module contains the main DocVaultSDK class that provides
the high-level API for document management.
"""

import logging
from typing import Any, BinaryIO, Dict, List, Optional
from uuid import UUID

from .config import Config
from .database.postgres_manager import PostgreSQLManager
from .database.repositories.agent import AgentRepository
from .database.repositories.organization import OrganizationRepository
from .database.schemas.acl import DocumentACL
from .database.schemas.permission import PermissionGrant

# Response models (v2.2)
from .database.schemas.responses import (
    DocumentDetails,
    DocumentListResponse,
    OwnershipTransferResponse,
    PermissionListResponse,
    SearchResponse,
)
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
        from doc_vault.services.agent_service import AgentService
        from doc_vault.services.organization_service import OrganizationService

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
        create_version: bool = True,
        change_description: Optional[str] = None,
    ):
        """
        Upload a document or create new version if exists.

        Supports multiple input types:
        - File path (str): '/path/to/file.pdf'
        - Text content (str): 'Document content text'
        - Bytes (bytes): b'binary content'
        - Binary stream (BinaryIO): open('file.pdf', 'rb')

        Args:
            file_input: File path (str), text content (str), bytes, or binary stream
            name: Document display name
            organization_id: Organization UUID or string
            agent_id: Agent UUID or string (uploader)
            description: Optional document description
            tags: Optional list of tags
            metadata: Optional custom metadata
            content_type: Optional MIME type (auto-detected if None)
            filename: Optional filename override
            prefix: Optional hierarchical prefix (e.g., '/reports/2025/')
            create_version: If True and document exists, create new version.
                           If False and document exists, replace current version.
            change_description: Description of changes (for versioning)

        Returns:
            Document: The uploaded/updated document

        Raises:
            ValidationError: If file_input type is invalid or parameters are invalid
            OrganizationNotFoundError: If organization doesn't exist
            AgentNotFoundError: If agent doesn't exist
            StorageError: If file upload fails
            PermissionDeniedError: If agent lacks WRITE permission (for updates)
            DocumentNotFoundError: If updating non-existent document

        Examples:
            Upload from file path::

                doc = await vault.upload(
                    file_input="/path/to/report.pdf",
                    name="Q4 Report",
                    organization_id=org_id,
                    agent_id=agent_id,
                    prefix="/reports/2025/q4/"
                )

            Upload text content::

                doc = await vault.upload(
                    file_input="This is my document content",
                    name="Meeting Notes",
                    organization_id=org_id,
                    agent_id=agent_id,
                    content_type="text/plain"
                )

            Upload bytes::

                content = requests.get(url).content
                doc = await vault.upload(
                    file_input=content,
                    name="Downloaded File",
                    organization_id=org_id,
                    agent_id=agent_id
                )

            Upload from stream::

                with open('large_file.zip', 'rb') as f:
                    doc = await vault.upload(
                        file_input=f,
                        name="Large Archive",
                        organization_id=org_id,
                        agent_id=agent_id
                    )

            Create new version of existing document::

                doc = await vault.upload(
                    file_input="/path/to/updated_report.pdf",
                    name="Q4 Report",
                    organization_id=org_id,
                    agent_id=agent_id,
                    create_version=True,
                    change_description="Updated with final numbers"
                )

            Replace current version (no history)::

                doc = await vault.upload(
                    file_input=corrected_bytes,
                    name="Q4 Report",
                    organization_id=org_id,
                    agent_id=agent_id,
                    create_version=False,
                    change_description="Fixed typo"
                )
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
            prefix=prefix,
            create_version=create_version,
            change_description=change_description,
        )

    async def download(
        self,
        document_id: UUID,
        agent_id: str | UUID,
        version: Optional[int] = None,
    ) -> bytes:
        """
        Download a document.

        Args:
            document_id: Document UUID
            agent_id: Agent UUID or string (requester)
            version: Optional version number (None = current)

        Returns:
            bytes: The document content

        Raises:
            ValidationError: If document_id or agent_id is invalid UUID format
            DocumentNotFoundError: If document doesn't exist
            AgentNotFoundError: If agent doesn't exist
            PermissionDeniedError: If agent lacks READ permission
            StorageError: If file retrieval from storage fails
            RuntimeError: If SDK is not initialized

        Note:
            agent_id accepts both UUID objects and string representations.
            The service layer handles automatic UUID conversion.
        """
        if not self._document_service:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )

        return await self._document_service.download_document(
            document_id=document_id,
            agent_id=agent_id,
            version=version,
        )

    async def update_metadata(
        self,
        document_id: UUID,
        agent_id: str | UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Update document metadata.

        Args:
            document_id: Document UUID
            agent_id: Agent UUID or string (updater)
            name: Optional new name
            description: Optional new description
            tags: Optional new tags
            metadata: Optional new metadata

        Returns:
            Document: Updated document

        Raises:
            ValidationError: If document_id or agent_id is invalid UUID format
            DocumentNotFoundError: If document doesn't exist
            AgentNotFoundError: If agent doesn't exist
            PermissionDeniedError: If agent lacks WRITE permission
            RuntimeError: If SDK is not initialized

        Note:
            agent_id accepts both UUID objects and string representations.
            The service layer handles automatic UUID conversion.
        """
        if not self._document_service:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )

        return await self._document_service.update_metadata(
            document_id=document_id,
            agent_id=agent_id,
            name=name,
            description=description,
            tags=tags,
            metadata=metadata,
        )

    async def delete(
        self,
        document_id: UUID,
        agent_id: str | UUID,
        hard_delete: bool = False,
    ) -> None:
        """
        Delete a document.

        Args:
            document_id: Document UUID
            agent_id: Agent UUID or string (deleter)
            hard_delete: If True, permanently delete; if False, soft delete

        Raises:
            ValidationError: If document_id or agent_id is invalid UUID format
            DocumentNotFoundError: If document doesn't exist
            AgentNotFoundError: If agent doesn't exist
            PermissionDeniedError: If agent lacks DELETE permission
            StorageError: If file removal from storage fails (hard_delete=True)
            RuntimeError: If SDK is not initialized

        Note:
            agent_id accepts both UUID objects and string representations.
            The service layer handles automatic UUID conversion.
        """
        if not self._document_service:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )

        await self._document_service.delete_document(
            document_id=document_id,
            agent_id=agent_id,
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
    ) -> DocumentListResponse:
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
            DocumentListResponse: Response model containing:
                - documents: List of Document instances
                - pagination: Pagination metadata (total, limit, offset, has_more)
                - filters: Applied filters

        Raises:
            ValidationError: If organization_id or agent_id is invalid UUID format
            OrganizationNotFoundError: If organization doesn't exist
            AgentNotFoundError: If agent doesn't exist
            RuntimeError: If SDK is not initialized

        Example:
            ```python
            # List all documents
            response = await vault.list_docs(
                organization_id=org_id,
                agent_id=agent_id,
                limit=50,
                offset=0
            )

            # Access response fields
            for doc in response.documents:
                print(f"{doc.name}: {doc.file_size} bytes")

            # Check pagination
            print(f"Total: {response.pagination.total}")
            print(f"Has more: {response.pagination.has_more}")

            # List documents with filters
            response = await vault.list_docs(
                organization_id=org_id,
                agent_id=agent_id,
                prefix="/reports/2025/",
                recursive=True,
                status="active",
                tags=["important"]
            )
            ```
        """
        if not self._document_service:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )

        return await self._document_service.list_documents_paginated(
            organization_id=organization_id,
            agent_id=agent_id,
            prefix=prefix,
            recursive=recursive,
            max_depth=max_depth,
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
    ) -> SearchResponse:
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
            SearchResponse: Response model containing:
                - documents: List of matching Document instances
                - query: The search query used
                - pagination: Pagination metadata (total, limit, offset, has_more)
                - filters: Applied filters

        Raises:
            ValidationError: If organization_id or agent_id is invalid UUID format
            OrganizationNotFoundError: If organization doesn't exist
            AgentNotFoundError: If agent doesn't exist
            RuntimeError: If SDK is not initialized

        Example:
            ```python
            # Search documents
            response = await vault.search(
                query="quarterly report",
                organization_id=org_id,
                agent_id=agent_id,
                status="active",
                limit=20
            )

            # Access results
            print(f"Found {response.pagination.total} documents matching '{response.query}'")
            for doc in response.documents:
                print(f"- {doc.name}")

            # Search with prefix filter
            response = await vault.search(
                query="budget",
                organization_id=org_id,
                agent_id=agent_id,
                prefix="/finance/",
                tags=["2025"]
            )
            ```
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

    # ==========================================================================
    # Additional v2.0 Methods
    # ==========================================================================

    async def get_document_details(
        self,
        document_id: str | UUID,
        agent_id: str | UUID,
        include_versions: bool = True,
        include_permissions: bool = False,
    ) -> DocumentDetails:
        """
        Get comprehensive document details with version and permission info.

        Args:
            document_id: Document UUID or string
            agent_id: Agent UUID or string
            include_versions: Include version history (default: True)
            include_permissions: Include permission details - requires ADMIN permission (default: False)

        Returns:
            DocumentDetails: Response model containing:
                - document: Document metadata
                - versions: List of DocumentVersion instances (if include_versions=True)
                - permissions: List of DocumentACL instances (if include_permissions=True and agent has ADMIN)
                - version_count: Total number of versions
                - current_version: Current version number

        Raises:
            DocumentNotFoundError: If document doesn't exist
            PermissionDeniedError: If agent lacks READ permission, or if include_permissions=True and agent lacks ADMIN permission
            AgentNotFoundError: If agent doesn't exist
            RuntimeError: If SDK is not initialized

        Example:
            ```python
            # Get basic document details with versions
            details = await vault.get_document_details(
                document_id=doc_id,
                agent_id=agent_id,
                include_versions=True
            )
            print(f"Document: {details.document.name}")
            print(f"Total versions: {details.version_count}")
            for version in details.versions:
                print(f"  v{version.version_number}: {version.change_description}")

            # Get full details including permissions (requires ADMIN)
            details = await vault.get_document_details(
                document_id=doc_id,
                agent_id=admin_id,
                include_versions=True,
                include_permissions=True
            )
            if details.permissions:
                for acl in details.permissions:
                    print(f"  {acl.agent_id}: {acl.permission}")
            ```
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
    ) -> OwnershipTransferResponse:
        """
        Transfer document ownership to another agent.

        Args:
            document_id: Document UUID or string
            new_owner_id: New owner agent UUID or string
            transferred_by: Transferring agent UUID or string (must be current owner)

        Returns:
            OwnershipTransferResponse: Response model containing:
                - document: Updated Document instance
                - old_owner: Previous owner UUID
                - new_owner: New owner UUID
                - transferred_by: Agent who performed transfer
                - transferred_at: Transfer timestamp
                - new_permissions: Updated permission list

        Raises:
            ValidationError: If any UUID parameter is invalid format
            DocumentNotFoundError: If document doesn't exist
            AgentNotFoundError: If new_owner_id or transferred_by agent doesn't exist
            PermissionDeniedError: If transferred_by agent is not the current owner (lacks ADMIN permission)
            RuntimeError: If SDK is not initialized

        Example:
            ```python
            # Transfer ownership
            response = await vault.transfer_ownership(
                document_id=doc_id,
                new_owner_id=new_agent_id,
                transferred_by=current_owner_id
            )
            print(f"Ownership transferred from {response.old_owner} to {response.new_owner}")
            print(f"Document: {response.document.name}")
            print(f"New permissions: {len(response.new_permissions)}")
            ```
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

    # Access Control & Permissions

    async def get_permissions(
        self,
        document_id: str | UUID,
        agent_id: Optional[str | UUID] = None,
    ) -> PermissionListResponse:
        """
        Get permissions for a document.

        Returns all permissions if agent_id is None, or permissions for specific agent.

        Args:
            document_id: Document UUID or string
            agent_id: Optional agent UUID/string to filter permissions

        Returns:
            PermissionListResponse: Response model containing:
                - document_id: The document UUID
                - permissions: List of DocumentACL instances
                - total: Total permission count
                - requested_by: Agent who requested permissions
                - requested_at: Timestamp of request

        Raises:
            DocumentNotFoundError: If document doesn't exist
            AgentNotFoundError: If agent_id provided but agent doesn't exist
            RuntimeError: If SDK is not initialized

        Example:
            ```python
            # Get all permissions for a document
            response = await vault.get_permissions(
                document_id=doc_id
            )
            print(f"Document has {response.total} permissions")
            for acl in response.permissions:
                print(f"  {acl.agent_id}: {acl.permission}")

            # Get permissions for specific agent
            response = await vault.get_permissions(
                document_id=doc_id,
                agent_id=agent_id
            )
            if response.permissions:
                print(f"Agent has: {response.permissions[0].permission}")
            ```
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
        permissions: List[PermissionGrant],
        granted_by: str | UUID,
    ) -> List[DocumentACL]:
        """
        Set permissions for a document in bulk.

        Replaces existing permissions with the provided list.

        Args:
            document_id: Document UUID or string
            permissions: List of PermissionGrant model instances with fields:
                - agent_id: UUID or string
                - permission: Permission level (READ, WRITE, DELETE, SHARE, ADMIN)
                - expires_at: Optional expiration datetime
                - metadata: Optional custom metadata
            granted_by: UUID or string of agent granting permissions

        Returns:
            List[DocumentACL]: List of created ACL instances

        Raises:
            ValidationError: If permission data is invalid
            DocumentNotFoundError: If document doesn't exist
            AgentNotFoundError: If granting agent or target agent doesn't exist
            PermissionDeniedError: If granting agent lacks ADMIN permission
            RuntimeError: If SDK is not initialized

        Example:
            ```python
            from doc_vault.database.schemas import PermissionGrant

            # Set permissions using PermissionGrant models
            acls = await vault.set_permissions(
                document_id=doc_id,
                permissions=[
                    PermissionGrant(agent_id=agent1, permission="READ"),
                    PermissionGrant(
                        agent_id=agent2,
                        permission="WRITE",
                        expires_at=datetime(2026, 1, 1)
                    ),
                ],
                granted_by=admin_id
            )

            # Access created permissions
            for acl in acls:
                print(f"{acl.agent_id} has {acl.permission} permission")
            ```
        """
        if not self._access_service:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )

        # Convert PermissionGrant objects to dicts for service layer
        perms_dicts = [perm.model_dump() for perm in permissions]

        return await self._access_service.set_permissions_bulk(
            document_id=document_id,
            permissions=perms_dicts,
            granted_by=granted_by,
        )

    # Version Management

    async def restore_version(
        self,
        document_id: UUID,
        version_number: int,
        agent_id: str | UUID,
        change_description: str,
    ):
        """
        Restore a previous version (creates new version).

        Args:
            document_id: Document UUID
            version_number: Version to restore
            agent_id: Agent UUID or string (restorer)
            change_description: Description of the restore

        Returns:
            DocumentVersion: New version created from restore

        Raises:
            ValidationError: If document_id or agent_id is invalid UUID format
            DocumentNotFoundError: If document doesn't exist
            AgentNotFoundError: If agent doesn't exist
            VersionNotFoundError: If specified version doesn't exist
            PermissionDeniedError: If agent lacks WRITE permission
            StorageError: If file restoration from storage fails
            RuntimeError: If SDK is not initialized

        Note:
            agent_id accepts both UUID objects and string representations.
            The service layer handles automatic UUID conversion.
        """
        if not self._version_service:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )

        return await self._version_service.restore_version(
            document_id=document_id,
            version_number=version_number,
            agent_id=agent_id,
            change_description=change_description,
        )

    # Organization & Agent Management

    async def register_organization(
        self,
        org_id: str | UUID,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Register a new organization (v2.0).

        Args:
            org_id: Organization UUID (UUID or string)
            metadata: Optional custom metadata

        Returns:
            Organization: The registered organization

        Raises:
            ValidationError: If org_id is invalid UUID
            OrganizationExistsError: If organization already exists
            RuntimeError: If SDK is not initialized

        Example:
            org = await vault.register_organization(
                org_id="550e8400-e29b-41d4-a716-446655440000",
                metadata={"display_name": "Acme Corp", "tier": "premium"}
            )
        """
        if not self._organization_service:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )

        return await self._organization_service.register_organization(
            org_id=org_id,
            metadata=metadata or {},
        )

    async def register_agent(
        self,
        agent_id: str | UUID,
        organization_id: str | UUID,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Register a new agent in an organization (v2.0).

        Args:
            agent_id: Agent UUID (UUID or string)
            organization_id: Organization UUID (UUID or string)
            metadata: Optional custom metadata

        Returns:
            Agent: The registered agent

        Raises:
            ValidationError: If UUIDs are invalid
            OrganizationNotFoundError: If organization doesn't exist
            AgentExistsError: If agent already exists
            RuntimeError: If SDK is not initialized

        Example:
            agent = await vault.register_agent(
                agent_id="550e8400-e29b-41d4-a716-446655440001",
                organization_id=org_id,
                metadata={
                    "name": "John Doe",
                    "email": "john@acme.com",
                    "role": "admin"
                }
            )
        """
        if not self._agent_service:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )

        return await self._agent_service.register_agent(
            agent_id=agent_id,
            organization_id=organization_id,
            metadata=metadata or {},
        )

    async def get_organization(
        self,
        org_id: str | UUID,
    ):
        """
        Get organization by ID (v2.0).

        Args:
            org_id: Organization UUID (UUID or string)

        Returns:
            Organization: The organization

        Raises:
            ValidationError: If org_id is invalid UUID
            OrganizationNotFoundError: If organization doesn't exist
            RuntimeError: If SDK is not initialized
        """
        if not self._db_manager:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )

        org_repo = OrganizationRepository(self._db_manager)
        org_uuid = org_id if isinstance(org_id, UUID) else UUID(org_id)
        org = await org_repo.get_by_id(org_uuid)
        if not org:
            raise OrganizationNotFoundError(
                f"Organization with ID '{org_id}' not found"
            )
        return org

    async def get_agent(
        self,
        agent_id: str | UUID,
    ):
        """
        Get agent by ID (v2.0).

        Args:
            agent_id: Agent UUID (UUID or string)

        Returns:
            Agent: The agent

        Raises:
            ValidationError: If agent_id is invalid UUID
            AgentNotFoundError: If agent doesn't exist
            RuntimeError: If SDK is not initialized
        """
        if not self._db_manager:
            raise RuntimeError(
                "SDK not initialized. Use 'async with DocVaultSDK() as sdk:'"
            )

        agent_repo = AgentRepository(self._db_manager)
        agent_uuid = agent_id if isinstance(agent_id, UUID) else UUID(agent_id)
        agent = await agent_repo.get_by_id(agent_uuid)
        if not agent:
            raise AgentNotFoundError(f"Agent with ID '{agent_id}' not found")
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
