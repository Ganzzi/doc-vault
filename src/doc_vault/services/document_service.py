"""
Document service for DocVault.

Provides business logic for document operations including upload, download,
metadata management, and search functionality.
"""

import logging
import mimetypes
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from doc_vault.database.postgres_manager import PostgreSQLManager
from doc_vault.database.repositories.acl import ACLRepository
from doc_vault.database.repositories.agent import AgentRepository
from doc_vault.database.repositories.document import DocumentRepository
from doc_vault.database.repositories.organization import OrganizationRepository
from doc_vault.database.repositories.version import VersionRepository
from doc_vault.database.schemas.document import Document, DocumentCreate
from doc_vault.database.schemas.version import DocumentVersion, DocumentVersionCreate
from doc_vault.exceptions import (
    AgentNotFoundError,
    DocumentNotFoundError,
    OrganizationNotFoundError,
    PermissionDeniedError,
    StorageError,
    ValidationError,
)
from doc_vault.storage.base import StorageBackend

logger = logging.getLogger(__name__)


class DocumentService:
    """
    Service for document operations.

    Orchestrates document-related business logic including CRUD operations,
    access control, versioning, and storage management.
    """

    def __init__(
        self,
        db_manager: PostgreSQLManager,
        storage_backend: StorageBackend,
        bucket_prefix: str = "doc-vault",
    ):
        """
        Initialize the DocumentService.

        Args:
            db_manager: Database connection manager
            storage_backend: Storage backend for file operations
            bucket_prefix: Prefix for bucket names
        """
        self.db_manager = db_manager
        self.storage_backend = storage_backend
        self.bucket_prefix = bucket_prefix

        # Initialize repositories
        self.document_repo = DocumentRepository(db_manager)
        self.version_repo = VersionRepository(db_manager)
        self.acl_repo = ACLRepository(db_manager)
        self.agent_repo = AgentRepository(db_manager)
        self.org_repo = OrganizationRepository(db_manager)

    def _ensure_uuid(self, value) -> UUID:
        """Convert string UUID to UUID object if needed."""
        if isinstance(value, str):
            return UUID(value)
        return value

    def _get_bucket_name(self, organization_id: UUID) -> str:
        """Generate bucket name for an organization."""
        return f"{self.bucket_prefix}-org-{str(organization_id)}"

    def _generate_storage_path(
        self, document_id: UUID, version_number: int, filename: str
    ) -> str:
        """Generate storage path for a document version."""
        return f"{document_id}/v{version_number}/{filename}"

    async def _check_agent_exists(self, agent_id: UUID | str) -> None:
        """Check if an agent exists."""
        agent_id = self._ensure_uuid(agent_id)
        agent = await self.agent_repo.get_by_id(agent_id)
        if not agent:
            raise AgentNotFoundError(f"Agent {agent_id} not found")

    async def _check_organization_exists(self, organization_id: UUID | str) -> None:
        """Check if an organization exists."""
        organization_id = self._ensure_uuid(organization_id)
        org = await self.org_repo.get_by_id(organization_id)
        if not org:
            raise OrganizationNotFoundError(f"Organization {organization_id} not found")

    async def _check_document_exists(self, document_id: UUID | str) -> Document:
        """Check if a document exists and return it."""
        document_id = self._ensure_uuid(document_id)
        document = await self.document_repo.get_by_id(document_id)
        if not document:
            raise DocumentNotFoundError(f"Document {document_id} not found")
        if document.status == "deleted":
            raise DocumentNotFoundError(f"Document {document_id} has been deleted")
        return document

    async def _check_permission(
        self, document_id: UUID | str, agent_id: UUID | str, permission: str
    ) -> None:
        """Check if an agent has permission for a document."""
        document_id = self._ensure_uuid(document_id)
        agent_id = self._ensure_uuid(agent_id)
        has_permission = await self.acl_repo.check_permission(
            document_id, agent_id, permission
        )
        if not has_permission:
            raise PermissionDeniedError(
                f"Agent {agent_id} does not have {permission} permission for document {document_id}"
            )

    async def _ensure_bucket_exists(self, bucket_name: str) -> None:
        """Ensure a bucket exists, creating it if necessary."""
        try:
            await self.storage_backend.create_bucket(bucket_name)
        except Exception as e:
            logger.warning(f"Could not create bucket {bucket_name}: {e}")
            # Bucket might already exist, which is fine

    async def upload_document(
        self,
        file_path: str,
        name: str,
        organization_id: UUID | str,
        agent_id: UUID | str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Document:
        """
        Upload a new document.

        Args:
            file_path: Path to the file to upload
            name: Display name for the document
            organization_id: Organization UUID
            agent_id: Agent UUID (uploader)
            description: Optional document description
            tags: Optional list of tags
            metadata: Optional custom metadata

        Returns:
            Created Document instance

        Raises:
            ValidationError: If file doesn't exist or validation fails
            AgentNotFoundError: If agent doesn't exist
            OrganizationNotFoundError: If organization doesn't exist
            StorageError: If upload fails
        """
        # Ensure UUIDs
        organization_id = self._ensure_uuid(organization_id)
        agent_id = self._ensure_uuid(agent_id)

        # Validate inputs
        if not os.path.exists(file_path):
            raise ValidationError(f"File does not exist: {file_path}")

        file_path_obj = Path(file_path)
        file_size = file_path_obj.stat().st_size
        filename = file_path_obj.name

        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(filename)
        if not mime_type:
            mime_type = "application/octet-stream"

        # Validate agent and organization exist
        await self._check_agent_exists(agent_id)
        await self._check_organization_exists(organization_id)

        # Read file content
        try:
            with open(file_path, "rb") as f:
                file_data = f.read()
        except Exception as e:
            raise StorageError(f"Failed to read file {file_path}: {e}")

        # Generate document ID and storage path
        document_id = uuid4()  # Generate UUID for document
        bucket_name = self._get_bucket_name(organization_id)
        storage_path = self._generate_storage_path(document_id, 1, filename)

        # Ensure bucket exists
        await self._ensure_bucket_exists(bucket_name)

        # Create document record
        create_data = DocumentCreate(
            id=document_id,
            organization_id=organization_id,
            name=name,
            description=description,
            filename=filename,
            file_size=file_size,
            mime_type=mime_type,
            storage_path=storage_path,
            created_by=agent_id,
            tags=tags or [],
            metadata=metadata or {},
        )

        # Use transaction for atomicity
        async with self.db_manager.connection() as conn:
            async with conn.transaction():
                # Create document in database
                document = await self.document_repo.create_from_create_schema(
                    create_data
                )

                # Upload file to storage
                try:
                    await self.storage_backend.upload(
                        bucket_name, storage_path, file_data, mime_type
                    )
                except Exception as e:
                    logger.error(f"Failed to upload file to storage: {e}")
                    raise StorageError(f"Failed to upload file: {e}") from e

                # Grant ADMIN permission to creator
                from doc_vault.database.schemas.acl import DocumentACLCreate

                acl_create = DocumentACLCreate(
                    document_id=document.id,
                    agent_id=agent_id,
                    permission="ADMIN",
                    granted_by=agent_id,
                )
                await self.acl_repo.create_from_create_schema(acl_create)

                # Create version record
                version_create = DocumentVersionCreate(
                    document_id=document.id,
                    version_number=1,
                    filename=filename,
                    file_size=file_size,
                    storage_path=storage_path,
                    mime_type=mime_type,
                    change_description="Initial upload",
                    change_type="create",
                    created_by=agent_id,
                    metadata=metadata or {},
                )
                await self.version_repo.create_from_create_schema(version_create)

        logger.info(f"Document uploaded: {document.id} by agent {agent_id}")
        return document

    async def download_document(
        self,
        document_id: UUID | str,
        agent_id: UUID | str,
        version: Optional[int] = None,
    ) -> bytes:
        """
        Download a document.

        Args:
            document_id: Document UUID
            agent_id: Agent UUID (requester)
            version: Optional version number (None for current)

        Returns:
            Document content as bytes

        Raises:
            DocumentNotFoundError: If document doesn't exist
            PermissionDeniedError: If agent lacks READ permission
            StorageError: If download fails
        """
        # Ensure UUIDs
        document_id = self._ensure_uuid(document_id)
        agent_id = self._ensure_uuid(agent_id)
        # Check agent exists
        await self._check_agent_exists(agent_id)

        # Get document
        document = await self._check_document_exists(document_id)

        # Check read permission
        await self._check_permission(document_id, agent_id, "READ")

        # Determine which version to download
        if version is None:
            version_number = document.current_version
            storage_path = document.storage_path
        else:
            # Get specific version
            version_info = await self.version_repo.get_by_document_and_version(
                document_id, version
            )
            if not version_info:
                raise ValidationError(
                    f"Version {version} not found for document {document_id}"
                )
            version_number = version_info.version_number
            storage_path = version_info.storage_path

        # Download from storage
        bucket_name = self._get_bucket_name(document.organization_id)
        try:
            file_data = await self.storage_backend.download(bucket_name, storage_path)
        except Exception as e:
            logger.error(f"Failed to download file from storage: {e}")
            raise StorageError(f"Failed to download file: {e}") from e

        logger.info(
            f"Document downloaded: {document_id} v{version_number} by agent {agent_id}"
        )
        return file_data

    async def update_metadata(
        self,
        document_id: UUID | str,
        agent_id: UUID | str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Document:
        """
        Update document metadata.

        Args:
            document_id: Document UUID
            agent_id: Agent UUID (updater)
            name: Optional new name
            description: Optional new description
            tags: Optional new tags
            metadata: Optional new metadata

        Returns:
            Updated Document instance

        Raises:
            DocumentNotFoundError: If document doesn't exist
            PermissionDeniedError: If agent lacks WRITE permission
        """
        # Ensure UUIDs
        document_id = self._ensure_uuid(document_id)
        agent_id = self._ensure_uuid(agent_id)

        # Check agent exists
        await self._check_agent_exists(agent_id)

        # Get document
        document = await self._check_document_exists(document_id)

        # Check write permission
        await self._check_permission(document_id, agent_id, "WRITE")

        # Prepare updates
        updates = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        if tags is not None:
            updates["tags"] = tags
        if metadata is not None:
            # Merge with existing metadata
            existing_metadata = document.metadata or {}
            existing_metadata.update(metadata)
            updates["metadata"] = existing_metadata

        updates["updated_by"] = agent_id

        # Update document
        updated_doc = await self.document_repo.update(document_id, updates)
        if not updated_doc:
            raise DocumentNotFoundError(f"Document {document_id} not found")

        logger.info(f"Document metadata updated: {document_id} by agent {agent_id}")
        return updated_doc

    async def delete_document(
        self,
        document_id: UUID | str,
        agent_id: UUID | str,
        hard_delete: bool = False,
    ) -> None:
        """
        Delete a document.

        Args:
            document_id: Document UUID
            agent_id: Agent UUID (deleter)
            hard_delete: If True, permanently delete; if False, soft delete

        Raises:
            DocumentNotFoundError: If document doesn't exist
            PermissionDeniedError: If agent lacks DELETE permission
        """
        # Ensure UUIDs
        document_id = self._ensure_uuid(document_id)
        agent_id = self._ensure_uuid(agent_id)

        # Check agent exists
        await self._check_agent_exists(agent_id)

        # Get document
        document = await self._check_document_exists(document_id)

        # Check delete permission
        await self._check_permission(document_id, agent_id, "DELETE")

        if hard_delete:
            # Hard delete: remove from storage and database
            bucket_name = self._get_bucket_name(document.organization_id)

            # Get all versions to delete from storage
            versions = await self.version_repo.get_by_document(document_id)
            storage_paths = [v.storage_path for v in versions]
            storage_paths.append(document.storage_path)  # Current version

            # Delete from storage (best effort)
            for path in storage_paths:
                try:
                    await self.storage_backend.delete(bucket_name, path)
                except Exception as e:
                    logger.warning(f"Failed to delete {path} from storage: {e}")

            # Delete from database
            await self.document_repo.hard_delete(document_id)
            logger.info(f"Document hard deleted: {document_id} by agent {agent_id}")
        else:
            # Soft delete: just mark as deleted
            await self.document_repo.update_status(document_id, "deleted", agent_id)
            logger.info(f"Document soft deleted: {document_id} by agent {agent_id}")

    async def replace_document(
        self,
        document_id: UUID | str,
        file_path: str,
        agent_id: UUID | str,
        change_description: str,
    ) -> DocumentVersion:
        """
        Replace document content with new version.

        Args:
            document_id: Document UUID
            file_path: Path to new file content
            agent_id: Agent UUID (updater)
            change_description: Description of the change

        Returns:
            Created DocumentVersion instance

        Raises:
            DocumentNotFoundError: If document doesn't exist
            PermissionDeniedError: If agent lacks WRITE permission
            ValidationError: If file doesn't exist
            StorageError: If upload fails
        """
        # Ensure UUIDs
        document_id = self._ensure_uuid(document_id)
        agent_id = self._ensure_uuid(agent_id)

        # Validate file
        if not os.path.exists(file_path):
            raise ValidationError(f"File does not exist: {file_path}")

        file_path_obj = Path(file_path)
        file_size = file_path_obj.stat().st_size
        filename = file_path_obj.name

        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(filename)
        if not mime_type:
            mime_type = "application/octet-stream"

        # Check agent exists
        await self._check_agent_exists(agent_id)

        # Get document
        document = await self._check_document_exists(document_id)

        # Check write permission
        await self._check_permission(document_id, agent_id, "WRITE")

        # Read new file content
        try:
            with open(file_path, "rb") as f:
                file_data = f.read()
        except Exception as e:
            raise StorageError(f"Failed to read file {file_path}: {e}")

        # Increment version
        new_version_number = document.current_version + 1
        bucket_name = self._get_bucket_name(document.organization_id)
        new_storage_path = self._generate_storage_path(
            document_id, new_version_number, filename
        )

        # Ensure bucket exists
        await self._ensure_bucket_exists(bucket_name)

        # Use transaction for atomicity
        async with self.db_manager.connection() as conn:
            async with conn.transaction():
                # Upload new version to storage
                try:
                    await self.storage_backend.upload(
                        bucket_name, new_storage_path, file_data, mime_type
                    )
                except Exception as e:
                    logger.error(f"Failed to upload new version to storage: {e}")
                    raise StorageError(f"Failed to upload new version: {e}") from e

                # Update document with new version info
                doc_updates = {
                    "current_version": new_version_number,
                    "filename": filename,
                    "file_size": file_size,
                    "mime_type": mime_type,
                    "storage_path": new_storage_path,
                    "updated_by": agent_id,
                }
                await self.document_repo.update(document_id, doc_updates)

                # Create version record
                version_create = DocumentVersionCreate(
                    document_id=document_id,
                    version_number=new_version_number,
                    filename=filename,
                    file_size=file_size,
                    storage_path=new_storage_path,
                    mime_type=mime_type,
                    change_description=change_description,
                    change_type="update",
                    created_by=agent_id,
                    metadata=document.metadata or {},
                )
                version = await self.version_repo.create_from_create_schema(
                    version_create
                )

        logger.info(
            f"Document replaced: {document_id} v{new_version_number} by agent {agent_id}"
        )
        return version

    async def list_documents(
        self,
        organization_id: UUID | str,
        agent_id: UUID | str,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Document]:
        """
        List documents accessible to an agent.

        Args:
            organization_id: Organization UUID
            agent_id: Agent UUID (requester)
            status: Optional status filter
            tags: Optional tag filter
            limit: Maximum number of documents
            offset: Number of documents to skip

        Returns:
            List of accessible Document instances

        Raises:
            AgentNotFoundError: If agent doesn't exist
            OrganizationNotFoundError: If organization doesn't exist
        """
        # Ensure UUIDs
        organization_id = self._ensure_uuid(organization_id)
        agent_id = self._ensure_uuid(agent_id)

        # Check agent and organization exist
        await self._check_agent_exists(agent_id)
        await self._check_organization_exists(organization_id)

        # Get all documents in organization with filters
        if tags:
            # Filter by tags
            documents = await self.document_repo.get_by_tags(
                organization_id, tags, limit, offset
            )
        else:
            # Get by organization
            documents = await self.document_repo.get_by_organization(
                organization_id, status, limit, offset
            )

        # Filter by permissions (this is a simplified approach)
        # In a production system, you'd want a more efficient query
        accessible_docs = []
        for doc in documents:
            try:
                await self._check_permission(doc.id, agent_id, "READ")
                accessible_docs.append(doc)
            except PermissionDeniedError:
                continue  # Skip documents user can't access

        return accessible_docs

    async def search_documents(
        self,
        query: str,
        organization_id: UUID | str,
        agent_id: UUID | str,
        limit: int = 20,
    ) -> List[Document]:
        """
        Search documents by name.

        Args:
            query: Search query
            organization_id: Organization UUID
            agent_id: Agent UUID (requester)
            limit: Maximum number of results

        Returns:
            List of matching Document instances

        Raises:
            AgentNotFoundError: If agent doesn't exist
            OrganizationNotFoundError: If organization doesn't exist
        """
        # Ensure UUIDs
        organization_id = self._ensure_uuid(organization_id)
        agent_id = self._ensure_uuid(agent_id)

        # Check agent and organization exist
        await self._check_agent_exists(agent_id)
        await self._check_organization_exists(organization_id)

        # Search by name (simplified - no full-text search implemented yet)
        documents = await self.document_repo.search_by_name(
            organization_id, query, limit
        )

        # Filter by permissions
        accessible_docs = []
        for doc in documents:
            try:
                await self._check_permission(doc.id, agent_id, "READ")
                accessible_docs.append(doc)
            except PermissionDeniedError:
                continue

        return accessible_docs

    # v2.0 Methods - Document Management with Prefix Support

    async def list_documents_by_prefix(
        self,
        organization_id: UUID | str,
        agent_id: UUID | str,
        prefix: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Document]:
        """
        List documents under a specific hierarchical prefix (v2.0).

        v2.0: Supports hierarchical document organization using prefixes.

        Args:
            organization_id: Organization UUID
            agent_id: Agent UUID (requester)
            prefix: Hierarchical prefix (e.g., '/reports/2025/q1/')
            limit: Maximum number of documents to return
            offset: Number of documents to skip

        Returns:
            List of Document instances under the prefix

        Raises:
            AgentNotFoundError: If agent doesn't exist
            OrganizationNotFoundError: If organization doesn't exist
            ValidationError: If parameters are invalid
            PermissionDeniedError: If agent lacks access to organization
        """
        try:
            organization_id = self._ensure_uuid(organization_id)
            agent_id = self._ensure_uuid(agent_id)

            # Verify organization and agent exist
            await self._check_organization_exists(organization_id)
            await self._check_agent_exists(agent_id)

            if limit < 1 or limit > 1000:
                raise ValidationError("limit must be between 1 and 1000")
            if offset < 0:
                raise ValidationError("offset must be >= 0")

            # List documents by prefix
            documents = await self.document_repo.list_by_prefix(
                organization_id, prefix, limit, offset
            )

            # Filter by permissions (agent must have READ access)
            accessible_docs = []
            for doc in documents:
                try:
                    await self._check_permission(doc.id, agent_id, "READ")
                    accessible_docs.append(doc)
                except PermissionDeniedError:
                    continue

            return accessible_docs

        except (AgentNotFoundError, OrganizationNotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Failed to list documents by prefix: {e}")
            raise ValidationError(f"Failed to list documents by prefix") from e

    async def list_documents_recursive(
        self,
        organization_id: UUID | str,
        agent_id: UUID | str,
        prefix: str,
        max_depth: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Document]:
        """
        List documents recursively under a prefix with depth control (v2.0).

        v2.0: Supports recursive listing with optional depth limit.

        Args:
            organization_id: Organization UUID
            agent_id: Agent UUID (requester)
            prefix: Starting prefix (e.g., '/reports/')
            max_depth: Optional maximum depth (None = unlimited)
            limit: Maximum number of documents to return
            offset: Number of documents to skip

        Returns:
            List of Document instances recursively under the prefix

        Raises:
            AgentNotFoundError: If agent doesn't exist
            OrganizationNotFoundError: If organization doesn't exist
            ValidationError: If parameters are invalid
        """
        try:
            organization_id = self._ensure_uuid(organization_id)
            agent_id = self._ensure_uuid(agent_id)

            # Verify organization and agent exist
            await self._check_organization_exists(organization_id)
            await self._check_agent_exists(agent_id)

            if limit < 1 or limit > 1000:
                raise ValidationError("limit must be between 1 and 1000")
            if offset < 0:
                raise ValidationError("offset must be >= 0")

            # List documents recursively
            documents = await self.document_repo.list_recursive(
                organization_id, prefix, max_depth, limit, offset
            )

            # Filter by permissions
            accessible_docs = []
            for doc in documents:
                try:
                    await self._check_permission(doc.id, agent_id, "READ")
                    accessible_docs.append(doc)
                except PermissionDeniedError:
                    continue

            return accessible_docs

        except (AgentNotFoundError, OrganizationNotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Failed to list documents recursively: {e}")
            raise ValidationError(f"Failed to list documents recursively") from e

    async def upload_document_to_prefix(
        self,
        file_path: str | bytes | Any,
        name: str,
        organization_id: UUID | str,
        agent_id: UUID | str,
        prefix: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Document:
        """
        Upload a document with hierarchical prefix (v2.0).

        v2.0: Supports uploading documents to hierarchical prefixes.

        Args:
            file_path: File path (str), bytes, or binary stream
            name: Document display name
            organization_id: Organization UUID
            agent_id: Agent UUID (requester)
            prefix: Optional hierarchical prefix (e.g., '/reports/2025/q1/')
            description: Optional document description
            tags: Optional list of tags
            metadata: Optional additional metadata

        Returns:
            Created Document instance

        Raises:
            AgentNotFoundError: If agent doesn't exist
            OrganizationNotFoundError: If organization doesn't exist
            ValidationError: If parameters are invalid
            StorageError: If storage operation fails
        """
        try:
            organization_id = self._ensure_uuid(organization_id)
            agent_id = self._ensure_uuid(agent_id)

            # Verify organization and agent exist
            await self._check_organization_exists(organization_id)
            await self._check_agent_exists(agent_id)

            # Validate prefix format if provided
            if prefix:
                if not prefix.startswith("/") or not prefix.endswith("/"):
                    raise ValidationError("Prefix must start and end with /")

            # Generate document ID if needed
            document_id = uuid4()

            # Determine file size and content type
            if isinstance(file_path, str):
                # File path
                file_size = Path(file_path).stat().st_size
                mime_type = (
                    mimetypes.guess_type(file_path)[0] or "application/octet-stream"
                )
                # Will read file during storage
            elif isinstance(file_path, bytes):
                file_size = len(file_path)
                mime_type = "application/octet-stream"
            else:
                # Binary stream - try to get size
                try:
                    file_size = len(file_path.read())
                    file_path.seek(0)  # Reset stream
                except Exception:
                    file_size = 0
                mime_type = "application/octet-stream"

            # Generate hierarchical path
            if prefix:
                path = f"{prefix}{name}"
            else:
                path = f"/{name}"

            # Generate storage path
            storage_path = self._generate_storage_path(document_id, 1, name)

            # Create document
            create_data = DocumentCreate(
                id=document_id,
                organization_id=organization_id,
                name=name,
                description=description,
                filename=Path(file_path).name if isinstance(file_path, str) else name,
                file_size=file_size,
                mime_type=mime_type,
                storage_path=storage_path,
                prefix=prefix,
                path=path,
                created_by=agent_id,
                updated_by=agent_id,
                tags=tags or [],
                metadata=metadata or {},
            )

            # Upload to storage
            bucket_name = self._get_bucket_name(organization_id)
            await self.storage_backend.put_object(bucket_name, storage_path, file_path)

            # Create document in database
            document = await self.document_repo.create(create_data)

            # Create initial version
            version_create = DocumentVersionCreate(
                document_id=document.id,
                version_number=1,
                filename=document.filename,
                file_size=document.file_size,
                storage_path=storage_path,
                mime_type=mime_type,
                change_description="Initial version",
                change_type="create",
                created_by=agent_id,
            )
            await self.version_repo.create(version_create)

            logger.info(
                f"Uploaded document {document_id} to prefix '{prefix}' "
                f"in organization {organization_id} by agent {agent_id}"
            )

            return document

        except (
            AgentNotFoundError,
            OrganizationNotFoundError,
            ValidationError,
            StorageError,
        ):
            raise
        except Exception as e:
            logger.error(f"Failed to upload document to prefix: {e}")
            raise StorageError(f"Failed to upload document") from e
