"""
Document service for DocVault.

Provides business logic for document operations including upload, download,
metadata management, and search functionality.
"""

import io
import logging
import mimetypes
import os
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Union
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

    def _extract_file_info(
        self, file_input: Union[str, bytes, BinaryIO]
    ) -> tuple[bytes, str, int]:
        """
        Extract file content, filename, and size from various input types.

        Args:
            file_input: File path (str), bytes, or binary stream

        Returns:
            Tuple of (file_content, filename, file_size)

        Raises:
            ValidationError: If input is invalid or unreadable
        """
        if isinstance(file_input, str):
            # File path
            if not os.path.exists(file_input):
                raise ValidationError(f"File does not exist: {file_input}")
            try:
                file_path = Path(file_input)
                file_size = file_path.stat().st_size
                filename = file_path.name
                with open(file_input, "rb") as f:
                    file_content = f.read()
                return file_content, filename, file_size
            except Exception as e:
                raise ValidationError(f"Failed to read file {file_input}: {e}")

        elif isinstance(file_input, bytes):
            # Bytes data
            return file_input, "document", len(file_input)

        elif isinstance(file_input, io.IOBase):
            # Binary stream
            try:
                current_pos = file_input.tell()
                file_input.seek(0, 2)  # Seek to end
                file_size = file_input.tell()
                file_input.seek(current_pos)  # Restore position
                file_content = file_input.read()
                file_input.seek(current_pos)  # Restore position again
                return file_content, "document", file_size
            except Exception as e:
                raise ValidationError(f"Failed to read from stream: {e}")

        else:
            raise ValidationError(
                f"Unsupported file input type: {type(file_input)}. "
                f"Must be str (path), bytes, or BinaryIO"
            )

    def _detect_mime_type(self, filename: str, content: Optional[bytes] = None) -> str:
        """
        Detect MIME type from filename and optionally content.

        Args:
            filename: Original filename
            content: Optional file content for magic detection

        Returns:
            MIME type string
        """
        # First try filename-based detection
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type:
            return mime_type

        # Could add magic detection here if needed
        return "application/octet-stream"

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

    async def upload_enhanced(
        self,
        file_input: Union[str, bytes, BinaryIO],
        name: str,
        organization_id: UUID | str,
        agent_id: UUID | str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        content_type: Optional[str] = None,
        filename: Optional[str] = None,
        prefix: Optional[str] = None,
        create_version: bool = True,
        change_description: Optional[str] = None,
    ) -> Document:
        """
        Upload a document or create new version if exists (v2.0).

        Supports multiple input types and version control:
        - str: File path to upload
        - bytes: Raw file content
        - BinaryIO: File-like object or stream

        If a document with the same name+org+prefix exists:
        - If create_version=True: Creates new version (preserves history)
        - If create_version=False: Replaces current version (no history)
        - If no document exists: Creates new document

        Args:
            file_input: File path (str), bytes, or binary stream
            name: Display name for the document
            organization_id: Organization UUID or string
            agent_id: Agent UUID (uploader)
            description: Optional document description
            tags: Optional list of tags
            metadata: Optional custom metadata
            content_type: Optional explicit MIME type (auto-detected if None)
            filename: Optional override for filename (auto-detected from path/name)
            prefix: Optional hierarchical prefix (e.g., '/reports/2025/')
            create_version: If True and document exists, create new version.
                           If False and document exists, replace current version.
            change_description: Description of changes (for versioning)

        Returns:
            Document instance (existing or newly created)

        Raises:
            ValidationError: If input is invalid
            AgentNotFoundError: If agent doesn't exist
            OrganizationNotFoundError: If organization doesn't exist
            StorageError: If upload fails
            PermissionDeniedError: If agent lacks WRITE permission (for updates)
        """
        # Ensure UUIDs
        organization_id = self._ensure_uuid(organization_id)
        agent_id = self._ensure_uuid(agent_id)

        # Validate agent and organization exist
        await self._check_agent_exists(agent_id)
        await self._check_organization_exists(organization_id)

        # Extract file info
        file_content, detected_filename, file_size = self._extract_file_info(file_input)

        # Use provided filename or detected one
        final_filename = filename or detected_filename
        if not final_filename or final_filename == "document":
            final_filename = f"{name}.bin"

        # Determine MIME type
        content_type or self._detect_mime_type(final_filename, file_content)

        # Check if document with same name+org+prefix already exists
        existing_doc = await self._find_existing_document(
            name=name, organization_id=organization_id, prefix=prefix
        )

        if existing_doc:
            # Document exists - handle version control
            logger.info(
                f"Document '{name}' already exists. "
                f"create_version={create_version}, agent={agent_id}"
            )

            # Use replace_document_content to handle versioning logic
            return await self.replace_document_content(
                document_id=existing_doc.id,
                file_input=file_input,
                agent_id=agent_id,
                change_description=change_description or f"Updated: {name}",
                create_version=create_version,
                content_type=content_type,
                filename=filename,
            )
        else:
            # New document - create with current behavior
            return await self._create_new_document(
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
            )

    async def _find_existing_document(
        self,
        name: str,
        organization_id: UUID,
        prefix: Optional[str] = None,
    ) -> Optional[Document]:
        """
        Find an existing document by name, org, and optional prefix.

        Args:
            name: Document name
            organization_id: Organization UUID
            prefix: Optional prefix

        Returns:
            Document if found, None otherwise
        """
        try:
            # Search by name in organization
            docs = await self.document_repo.search_by_name(
                organization_id=organization_id,
                name_query=f"^{name}$",  # Exact match
                limit=1,
            )

            if not docs:
                return None

            # If prefix specified, check it matches
            if prefix is not None:
                doc = docs[0]
                if doc.prefix == prefix:
                    return doc
                return None

            # No prefix specified, return first match
            return docs[0]
        except Exception as e:
            logger.debug(f"Error finding existing document: {e}")
            return None

    async def _create_new_document(
        self,
        file_input: Union[str, bytes, BinaryIO],
        name: str,
        organization_id: UUID,
        agent_id: UUID,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        content_type: Optional[str] = None,
        filename: Optional[str] = None,
        prefix: Optional[str] = None,
    ) -> Document:
        """
        Create a new document from scratch.

        Args:
            file_input: File path (str), bytes, or binary stream
            name: Display name
            organization_id: Organization UUID
            agent_id: Agent UUID
            description: Optional description
            tags: Optional tags
            metadata: Optional metadata
            content_type: Optional MIME type
            filename: Optional filename override
            prefix: Optional prefix

        Returns:
            Created Document instance
        """
        # Extract file info
        file_content, detected_filename, file_size = self._extract_file_info(file_input)

        # Use provided filename or detected one
        final_filename = filename or detected_filename
        if not final_filename or final_filename == "document":
            final_filename = f"{name}.bin"

        # Determine MIME type
        mime_type = content_type or self._detect_mime_type(final_filename, file_content)

        # Generate document ID and storage path
        document_id = uuid4()
        bucket_name = self._get_bucket_name(organization_id)
        storage_path = self._generate_storage_path(document_id, 1, final_filename)

        # Ensure bucket exists
        await self._ensure_bucket_exists(bucket_name)

        # Build path from prefix and name
        if prefix:
            path = f"{prefix}{name}"
        else:
            path = f"/{name}"

        # Create document record in transaction
        create_data = DocumentCreate(
            id=document_id,
            organization_id=organization_id,
            name=name,
            description=description,
            filename=final_filename,
            file_size=file_size,
            mime_type=mime_type,
            storage_path=storage_path,
            prefix=prefix,
            path=path,
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
                        bucket_name, storage_path, file_content, mime_type
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
                    filename=final_filename,
                    file_size=file_size,
                    storage_path=storage_path,
                    mime_type=mime_type,
                    change_description="Initial upload",
                    change_type="create",
                    created_by=agent_id,
                    metadata=metadata or {},
                )
                await self.version_repo.create_from_create_schema(version_create)

        logger.info(f"Created new document: {document.id} by agent {agent_id}")
        return document

    async def replace_document_content(
        self,
        document_id: UUID | str,
        file_input: Union[str, bytes, BinaryIO],
        agent_id: UUID | str,
        change_description: str,
        create_version: bool = True,
        content_type: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> DocumentVersion | Document:
        """
        Replace document content with flexible input support (v2.0).

        Can optionally skip version creation and directly replace the content
        of the current version (useful for file uploads that shouldn't create
        historical versions).

        Args:
            document_id: Document UUID
            file_input: File path (str), bytes, or binary stream
            agent_id: Agent UUID (updater)
            change_description: Description of the change
            create_version: If True, create new version; if False, replace current
            content_type: Optional explicit MIME type (auto-detected if None)
            filename: Optional override for filename

        Returns:
            DocumentVersion if create_version=True, Document if False

        Raises:
            DocumentNotFoundError: If document doesn't exist
            PermissionDeniedError: If agent lacks WRITE permission
            ValidationError: If input is invalid
            StorageError: If upload fails
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

        # Extract file info
        file_content, detected_filename, file_size = self._extract_file_info(file_input)

        # Use provided filename or detected one or keep original
        final_filename = filename or detected_filename or document.filename
        if final_filename == "document":
            final_filename = document.filename

        # Determine MIME type
        mime_type = content_type or self._detect_mime_type(final_filename, file_content)

        bucket_name = self._get_bucket_name(document.organization_id)

        if create_version:
            # Create new version (traditional behavior)
            new_version_number = document.current_version + 1
            new_storage_path = self._generate_storage_path(
                document_id, new_version_number, final_filename
            )

            # Use transaction for atomicity
            async with self.db_manager.connection() as conn:
                async with conn.transaction():
                    # Upload new version to storage
                    try:
                        await self.storage_backend.upload(
                            bucket_name, new_storage_path, file_content, mime_type
                        )
                    except Exception as e:
                        logger.error(f"Failed to upload new version to storage: {e}")
                        raise StorageError(f"Failed to upload new version: {e}") from e

                    # Update document with new version info
                    doc_updates = {
                        "current_version": new_version_number,
                        "filename": final_filename,
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
                        filename=final_filename,
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
                f"Document replaced (v{new_version_number}): {document_id} by agent {agent_id}"
            )
            return version

        else:
            # Replace current version without creating new version
            # Useful for file updates that shouldn't create history
            storage_path = document.storage_path

            async with self.db_manager.connection() as conn:
                async with conn.transaction():
                    # Delete old file from storage
                    try:
                        await self.storage_backend.delete(bucket_name, storage_path)
                    except Exception as e:
                        logger.warning(
                            f"Failed to delete old version from storage: {e}"
                        )

                    # Upload new content to same location
                    try:
                        await self.storage_backend.upload(
                            bucket_name, storage_path, file_content, mime_type
                        )
                    except Exception as e:
                        logger.error(f"Failed to upload replacement file: {e}")
                        raise StorageError(
                            f"Failed to upload replacement file: {e}"
                        ) from e

                    # Update document metadata only
                    doc_updates = {
                        "filename": final_filename,
                        "file_size": file_size,
                        "mime_type": mime_type,
                        "updated_by": agent_id,
                    }
                    updated_doc = await self.document_repo.update(
                        document_id, doc_updates
                    )

                    # Update the current version record with new metadata
                    version_updates = {
                        "filename": final_filename,
                        "file_size": file_size,
                        "storage_path": storage_path,
                        "mime_type": mime_type,
                    }
                    await self.version_repo.update(
                        document.current_version, version_updates
                    )

            logger.info(
                f"Document content replaced (no version): {document_id} by agent {agent_id}"
            )
            return updated_doc

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
            raise ValidationError("Failed to list documents by prefix") from e

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
            raise ValidationError("Failed to list documents recursively") from e

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
            raise StorageError("Failed to upload document") from e

    # Phase 7: Document Listing & Retrieval

    async def get_document_details(
        self,
        document_id: UUID | str,
        agent_id: UUID | str,
        include_versions: bool = True,
        include_permissions: bool = False,
    ) -> Dict[str, Any]:
        """
        Get comprehensive document details including version history and permissions (v2.0).

        Retrieves complete document information with optional version history
        and permission details.

        Args:
            document_id: Document UUID
            agent_id: Agent UUID (requester)
            include_versions: If True, include full version history
            include_permissions: If True, include all permissions for document (requires ADMIN)

        Returns:
            Dictionary with document details, versions, and optionally permissions

        Raises:
            DocumentNotFoundError: If document doesn't exist
            PermissionDeniedError: If agent lacks READ permission, or if include_permissions=True and agent lacks ADMIN permission
            AgentNotFoundError: If agent doesn't exist
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

        # Build response
        details = {
            "id": str(document.id),
            "name": document.name,
            "description": document.description,
            "filename": document.filename,
            "file_size": document.file_size,
            "mime_type": document.mime_type,
            "status": document.status,
            "organization_id": str(document.organization_id),
            "created_by": str(document.created_by),
            "created_at": document.created_at.isoformat(),
            "updated_by": str(document.updated_by),
            "updated_at": document.updated_at.isoformat(),
            "current_version": document.current_version,
            "tags": document.tags,
            "metadata": document.metadata,
            "prefix": document.prefix,
            "path": document.path,
        }

        # Include version history if requested
        if include_versions:
            versions = await self.version_repo.get_by_document(document_id)
            details["versions"] = [
                {
                    "version_number": v.version_number,
                    "filename": v.filename,
                    "file_size": v.file_size,
                    "mime_type": v.mime_type,
                    "storage_path": v.storage_path,
                    "change_description": v.change_description,
                    "change_type": v.change_type,
                    "created_by": str(v.created_by),
                    "created_at": v.created_at.isoformat(),
                    "metadata": v.metadata,
                }
                for v in versions
            ]

        # Include permissions if requested (ADMIN only)
        if include_permissions:
            # Security check: Only document owners (ADMIN permission) can view permissions
            agent_acls = await self.acl_repo.get_by_document_and_agent(
                document_id, agent_id
            )
            is_owner = any(acl.permission == "ADMIN" for acl in agent_acls)

            if not is_owner:
                raise PermissionDeniedError(
                    "Only document owners (ADMIN permission) can view permissions"
                )

            # Agent is owner - include all permissions
            acls = await self.acl_repo.get_by_document(document_id)
            details["permissions"] = [
                {
                    "agent_id": str(acl.agent_id),
                    "permission": acl.permission,
                    "granted_by": str(acl.granted_by),
                    "granted_at": acl.granted_at.isoformat(),
                    "expires_at": (
                        acl.expires_at.isoformat() if acl.expires_at else None
                    ),
                }
                for acl in acls
            ]

        logger.info(f"Retrieved document details: {document_id} for agent {agent_id}")
        return details

    async def list_documents_paginated(
        self,
        organization_id: UUID | str,
        agent_id: UUID | str,
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
        List documents with hierarchical filtering, pagination, and sorting (v2.0).

        Enhanced listing with prefix-based hierarchical organization, filtering,
        sorting, and pagination metadata.

        Args:
            organization_id: Organization UUID
            agent_id: Agent UUID (requester)
            prefix: Optional prefix filter (e.g., '/reports/2025/')
            recursive: If True, list all documents under prefix recursively
            max_depth: Maximum recursion depth (None = unlimited)
            status: Optional status filter (active, deleted, archived)
            tags: Optional tag filter (all tags must match)
            limit: Maximum documents per page (1-1000)
            offset: Number of documents to skip
            sort_by: Sort field (created_at, updated_at, name, file_size)
            sort_order: Sort direction (asc, desc)

        Returns:
            Dictionary with documents list and pagination metadata

        Raises:
            AgentNotFoundError: If agent doesn't exist
            OrganizationNotFoundError: If organization doesn't exist
            ValidationError: If parameters are invalid
        """
        # Ensure UUIDs
        organization_id = self._ensure_uuid(organization_id)
        agent_id = self._ensure_uuid(agent_id)

        # Validate inputs
        if not (1 <= limit <= 1000):
            raise ValidationError("limit must be between 1 and 1000")
        if offset < 0:
            raise ValidationError("offset must be >= 0")

        allowed_sort_fields = {"created_at", "updated_at", "name", "file_size"}
        if sort_by not in allowed_sort_fields:
            raise ValidationError(f"sort_by must be one of {allowed_sort_fields}")

        allowed_orders = {"asc", "desc"}
        if sort_order not in allowed_orders:
            raise ValidationError(f"sort_order must be one of {allowed_orders}")

        # Check agent and organization exist
        await self._check_agent_exists(agent_id)
        await self._check_organization_exists(organization_id)

        # Get documents based on filtering
        if prefix and recursive:
            # Recursive listing under prefix with optional depth limit
            documents = await self.document_repo.list_recursive(
                organization_id=organization_id,
                prefix=prefix,
                max_depth=max_depth,
                limit=limit,
                offset=offset,
            )
        elif prefix:
            # Flat listing with exact prefix match
            documents = await self.document_repo.list_by_prefix(
                org_id=organization_id,
                prefix=prefix,
                limit=limit,
                offset=offset,
            )
        elif tags:
            # List by tags
            documents = await self.document_repo.get_by_tags(
                organization_id, tags, limit, offset
            )
        else:
            # List all documents in organization
            documents = await self.document_repo.get_by_organization(
                organization_id, status, limit, offset
            )

        # Filter by permissions
        accessible_docs = []
        for doc in documents:
            try:
                await self._check_permission(doc.id, agent_id, "READ")
                accessible_docs.append(doc)
            except PermissionDeniedError:
                continue

        # Convert to dictionaries
        docs_list = [
            {
                "id": str(d.id),
                "name": d.name,
                "description": d.description,
                "filename": d.filename,
                "file_size": d.file_size,
                "mime_type": d.mime_type,
                "status": d.status,
                "created_at": d.created_at.isoformat(),
                "updated_at": d.updated_at.isoformat(),
                "tags": d.tags,
                "prefix": d.prefix,
                "path": d.path,
                "current_version": d.current_version,
            }
            for d in accessible_docs
        ]

        # Return with pagination metadata
        return {
            "documents": docs_list,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "count": len(docs_list),
                "total_available": len(accessible_docs),
            },
            "filters": {
                "prefix": prefix,
                "recursive": recursive,
                "max_depth": max_depth,
                "status": status,
                "tags": tags,
                "sort_by": sort_by,
                "sort_order": sort_order,
            },
        }

    async def search_documents_enhanced(
        self,
        query: str,
        organization_id: UUID | str,
        agent_id: UUID | str,
        prefix: Optional[str] = None,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Enhanced document search with filters (v2.0).

        Search documents by query with optional filtering by prefix, status,
        and tags.

        Args:
            query: Search query string
            organization_id: Organization UUID
            agent_id: Agent UUID (requester)
            prefix: Optional prefix filter
            status: Optional status filter
            tags: Optional tag filter
            limit: Maximum results (1-100)
            offset: Number of results to skip

        Returns:
            Dictionary with search results and metadata

        Raises:
            AgentNotFoundError: If agent doesn't exist
            OrganizationNotFoundError: If organization doesn't exist
            ValidationError: If parameters are invalid
        """
        # Ensure UUIDs
        organization_id = self._ensure_uuid(organization_id)
        agent_id = self._ensure_uuid(agent_id)

        # Validate inputs
        if not query or len(query.strip()) < 2:
            raise ValidationError("query must be at least 2 characters")
        if not (1 <= limit <= 100):
            raise ValidationError("limit must be between 1 and 100")
        if offset < 0:
            raise ValidationError("offset must be >= 0")

        # Check agent and organization exist
        await self._check_agent_exists(agent_id)
        await self._check_organization_exists(organization_id)

        # Search documents
        documents = await self.document_repo.search_by_name(
            organization_id, query, limit
        )

        # Apply additional filters
        filtered_docs = []
        for doc in documents:
            # Filter by prefix if provided
            if prefix and not (doc.prefix and doc.prefix.startswith(prefix)):
                continue

            # Filter by status if provided
            if status and doc.status != status:
                continue

            # Filter by tags if provided
            if tags and not all(tag in doc.tags for tag in tags):
                continue

            # Check permission
            try:
                await self._check_permission(doc.id, agent_id, "READ")
                filtered_docs.append(doc)
            except PermissionDeniedError:
                continue

        # Apply offset to results
        final_results = filtered_docs[offset : offset + limit]

        # Convert to dictionaries
        results_list = [
            {
                "id": str(d.id),
                "name": d.name,
                "description": d.description,
                "filename": d.filename,
                "file_size": d.file_size,
                "status": d.status,
                "created_at": d.created_at.isoformat(),
                "prefix": d.prefix,
                "relevance_score": 1.0,  # TODO: implement actual relevance scoring
            }
            for d in final_results
        ]

        logger.info(
            f"Enhanced search: {query} in org {organization_id} - {len(results_list)} results"
        )
        return {
            "query": query,
            "results": results_list,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "count": len(results_list),
                "total_matching": len(filtered_docs),
            },
            "filters": {
                "prefix": prefix,
                "status": status,
                "tags": tags,
            },
        }
