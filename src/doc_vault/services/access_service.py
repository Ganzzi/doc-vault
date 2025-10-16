"""
Access control service for DocVault.

Provides business logic for managing document permissions and access control.
"""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from doc_vault.database.postgres_manager import PostgreSQLManager
from doc_vault.database.repositories.acl import ACLRepository
from doc_vault.database.repositories.agent import AgentRepository
from doc_vault.database.repositories.document import DocumentRepository
from doc_vault.database.repositories.organization import OrganizationRepository
from doc_vault.database.schemas.acl import DocumentACL, DocumentACLCreate
from doc_vault.database.schemas.document import Document
from doc_vault.exceptions import (
    AgentNotFoundError,
    DocumentNotFoundError,
    OrganizationNotFoundError,
    PermissionDeniedError,
    ValidationError,
)

logger = logging.getLogger(__name__)


class AccessService:
    """
    Service for access control operations.

    Manages document permissions, sharing, and access validation.
    """

    def __init__(self, db_manager: PostgreSQLManager):
        """
        Initialize the AccessService.

        Args:
            db_manager: Database connection manager
        """
        self.db_manager = db_manager

        # Initialize repositories
        self.acl_repo = ACLRepository(db_manager)
        self.document_repo = DocumentRepository(db_manager)
        self.agent_repo = AgentRepository(db_manager)
        self.org_repo = OrganizationRepository(db_manager)

    async def _check_agent_exists(self, agent_id: UUID) -> None:
        """Check if an agent exists."""
        agent = await self.agent_repo.get_by_id(agent_id)
        if not agent:
            raise AgentNotFoundError(f"Agent {agent_id} not found")

    async def _check_document_exists(self, document_id: UUID) -> Document:
        """Check if a document exists and return it."""
        document = await self.document_repo.get_by_id(document_id)
        if not document:
            raise DocumentNotFoundError(f"Document {document_id} not found")
        if document.status == "deleted":
            raise DocumentNotFoundError(f"Document {document_id} has been deleted")
        return document

    async def _check_share_permission(self, document_id: UUID, agent_id: UUID) -> None:
        """Check if an agent has permission to share a document."""
        # Agent must have either ADMIN or SHARE permission
        has_admin = await self.acl_repo.check_permission(document_id, agent_id, "ADMIN")
        has_share = await self.acl_repo.check_permission(document_id, agent_id, "SHARE")

        if not (has_admin or has_share):
            raise PermissionDeniedError(
                f"Agent {agent_id} does not have permission to share document {document_id}"
            )

    async def _validate_permission(self, permission: str) -> None:
        """Validate that permission is one of the allowed values."""
        allowed_permissions = {"READ", "WRITE", "DELETE", "SHARE", "ADMIN"}
        if permission not in allowed_permissions:
            raise ValidationError(
                f"Invalid permission '{permission}'. Must be one of: {', '.join(allowed_permissions)}"
            )

    async def grant_access(
        self,
        document_id: UUID,
        agent_id: UUID,
        permission: str,
        granted_by: UUID,
        expires_at: Optional[datetime] = None,
    ) -> DocumentACL:
        """
        Grant access permission to a document for an agent.

        Args:
            document_id: Document UUID
            agent_id: Agent UUID to grant access to
            permission: Permission to grant ('READ', 'WRITE', 'DELETE', 'SHARE', 'ADMIN')
            granted_by: Agent UUID granting the permission
            expires_at: Optional expiration datetime

        Returns:
            Created DocumentACL instance

        Raises:
            DocumentNotFoundError: If document doesn't exist
            AgentNotFoundError: If agent doesn't exist
            PermissionDeniedError: If granter lacks sharing permission
            ValidationError: If permission is invalid
        """
        # Validate permission
        self._validate_permission(permission)

        # Check agents exist
        await self._check_agent_exists(agent_id)
        await self._check_agent_exists(granted_by)

        # Check document exists
        document = await self._check_document_exists(document_id)

        # Check that granter has permission to share
        await self._check_share_permission(document_id, granted_by)

        # Check if permission already exists
        existing_permissions = await self.acl_repo.get_by_document_and_agent(
            document_id, agent_id
        )

        # Check if this specific permission already exists
        for existing in existing_permissions:
            if existing.permission == permission:
                # Update expiration if different
                if existing.expires_at != expires_at:
                    updates = {"expires_at": expires_at}
                    updated = await self.acl_repo.update(existing.id, updates)
                    logger.info(
                        f"Updated permission: {permission} for agent {agent_id} "
                        f"on document {document_id} by {granted_by}"
                    )
                    return updated
                else:
                    # Permission already exists with same expiration
                    logger.info(
                        f"Permission already exists: {permission} for agent {agent_id} "
                        f"on document {document_id}"
                    )
                    return existing

        # Create new permission
        acl_create = DocumentACLCreate(
            document_id=document_id,
            agent_id=agent_id,
            permission=permission,
            granted_by=granted_by,
            expires_at=expires_at,
        )

        acl = await self.acl_repo.create_from_create_schema(acl_create)

        logger.info(
            f"Granted permission: {permission} for agent {agent_id} "
            f"on document {document_id} by {granted_by}"
        )
        return acl

    async def revoke_access(
        self,
        document_id: UUID,
        agent_id: UUID,
        permission: str,
        revoked_by: UUID,
    ) -> None:
        """
        Revoke access permission from a document for an agent.

        Args:
            document_id: Document UUID
            agent_id: Agent UUID to revoke access from
            permission: Permission to revoke
            revoked_by: Agent UUID revoking the permission

        Raises:
            DocumentNotFoundError: If document doesn't exist
            AgentNotFoundError: If agent doesn't exist
            PermissionDeniedError: If revoker lacks sharing permission
            ValidationError: If permission is invalid
        """
        # Validate permission
        self._validate_permission(permission)

        # Check agents exist
        await self._check_agent_exists(agent_id)
        await self._check_agent_exists(revoked_by)

        # Check document exists
        await self._check_document_exists(document_id)

        # Check that revoker has permission to manage sharing
        await self._check_share_permission(document_id, revoked_by)

        # Find the specific permission to revoke
        existing_permissions = await self.acl_repo.get_by_document_and_agent(
            document_id, agent_id
        )

        permission_to_revoke = None
        for existing in existing_permissions:
            if existing.permission == permission:
                permission_to_revoke = existing
                break

        if not permission_to_revoke:
            logger.warning(
                f"Permission {permission} not found for agent {agent_id} "
                f"on document {document_id}"
            )
            return  # Idempotent - permission doesn't exist

        # Delete the permission
        await self.acl_repo.delete(permission_to_revoke.id)

        logger.info(
            f"Revoked permission: {permission} from agent {agent_id} "
            f"on document {document_id} by {revoked_by}"
        )

    async def check_permission(
        self,
        document_id: UUID,
        agent_id: UUID,
        permission: str,
    ) -> bool:
        """
        Check if an agent has a specific permission for a document.

        Args:
            document_id: Document UUID
            agent_id: Agent UUID
            permission: Permission to check

        Returns:
            True if agent has the permission, False otherwise

        Raises:
            DocumentNotFoundError: If document doesn't exist
            AgentNotFoundError: If agent doesn't exist
            ValidationError: If permission is invalid
        """
        # Validate permission
        self._validate_permission(permission)

        # Check agents and document exist
        await self._check_agent_exists(agent_id)
        await self._check_document_exists(document_id)

        # Check permission
        has_permission = await self.acl_repo.check_permission(
            document_id, agent_id, permission
        )

        return has_permission

    async def list_accessible_documents(
        self,
        agent_id: UUID,
        organization_id: UUID,
        permission: Optional[str] = None,
    ) -> List[Document]:
        """
        List all documents an agent can access in an organization.

        Args:
            agent_id: Agent UUID
            organization_id: Organization UUID
            permission: Optional permission filter (defaults to 'READ')

        Returns:
            List of accessible Document instances

        Raises:
            AgentNotFoundError: If agent doesn't exist
            OrganizationNotFoundError: If organization doesn't exist
            ValidationError: If permission is invalid
        """
        # Validate permission if provided
        if permission:
            self._validate_permission(permission)
        else:
            permission = "READ"  # Default to READ permission

        # Check agent and organization exist
        await self._check_agent_exists(agent_id)
        org = await self.org_repo.get_by_id(organization_id)
        if not org:
            raise OrganizationNotFoundError(f"Organization {organization_id} not found")

        # Get all documents in the organization
        documents = await self.document_repo.get_by_organization(organization_id)

        # Filter by accessibility
        accessible_docs = []
        for doc in documents:
            try:
                has_access = await self.acl_repo.check_permission(
                    doc.id, agent_id, permission
                )
                if has_access:
                    accessible_docs.append(doc)
            except Exception as e:
                logger.warning(f"Error checking permission for document {doc.id}: {e}")
                continue

        return accessible_docs

    async def get_document_permissions(
        self,
        document_id: UUID,
        agent_id: UUID,
    ) -> List[DocumentACL]:
        """
        Get all permissions for a document.

        Args:
            document_id: Document UUID
            agent_id: Agent UUID (must have ADMIN permission)

        Returns:
            List of DocumentACL instances for the document

        Raises:
            DocumentNotFoundError: If document doesn't exist
            AgentNotFoundError: If agent doesn't exist
            PermissionDeniedError: If agent lacks ADMIN permission
        """
        # Check agent exists
        await self._check_agent_exists(agent_id)

        # Check document exists
        await self._check_document_exists(document_id)

        # Check that requester has ADMIN permission
        await self._check_permission(document_id, agent_id, "ADMIN")

        # Get all permissions for the document
        permissions = await self.acl_repo.get_by_document(document_id)

        return permissions
