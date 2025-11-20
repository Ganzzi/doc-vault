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

    def _ensure_uuid(self, value) -> UUID:
        """Convert string UUID to UUID object if needed."""
        if isinstance(value, str):
            return UUID(value)
        return value

    async def _check_agent_exists(self, agent_id: UUID | str) -> None:
        """Check if an agent exists."""
        agent_id = self._ensure_uuid(agent_id)
        agent = await self.agent_repo.get_by_id(agent_id)
        if not agent:
            raise AgentNotFoundError(f"Agent {agent_id} not found")

    async def _check_document_exists(self, document_id: UUID | str) -> Document:
        """Check if a document exists and return it."""
        document_id = self._ensure_uuid(document_id)
        document = await self.document_repo.get_by_id(document_id)
        if not document:
            raise DocumentNotFoundError(f"Document {document_id} not found")
        if document.status == "deleted":
            raise DocumentNotFoundError(f"Document {document_id} has been deleted")
        return document

    async def _check_share_permission(
        self, document_id: UUID | str, agent_id: UUID | str
    ) -> None:
        """Check if an agent has permission to share a document."""
        document_id = self._ensure_uuid(document_id)
        agent_id = self._ensure_uuid(agent_id)
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
        document_id: UUID | str,
        agent_id: UUID | str,
        permission: str,
        granted_by: UUID | str,
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
        # Ensure UUIDs
        document_id = self._ensure_uuid(document_id)
        agent_id = self._ensure_uuid(agent_id)
        granted_by = self._ensure_uuid(granted_by)

        # Validate permission
        await self._validate_permission(permission)

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
        document_id: UUID | str,
        agent_id: UUID | str,
        permission: str,
        revoked_by: UUID | str,
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
        # Ensure UUIDs
        document_id = self._ensure_uuid(document_id)
        agent_id = self._ensure_uuid(agent_id)
        revoked_by = self._ensure_uuid(revoked_by)

        # Validate permission
        await self._validate_permission(permission)

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
        document_id: UUID | str,
        agent_id: UUID | str,
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
        # Ensure UUIDs
        document_id = self._ensure_uuid(document_id)
        agent_id = self._ensure_uuid(agent_id)

        # Validate permission
        await self._validate_permission(permission)

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
        agent_id: UUID | str,
        organization_id: UUID | str,
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
        # Ensure UUIDs
        agent_id = self._ensure_uuid(agent_id)
        organization_id = self._ensure_uuid(organization_id)

        # Validate permission if provided
        if permission:
            await self._validate_permission(permission)
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
        document_id: UUID | str,
        agent_id: UUID | str,
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
        # Ensure UUIDs
        document_id = self._ensure_uuid(document_id)
        agent_id = self._ensure_uuid(agent_id)

        # Check agent exists
        await self._check_agent_exists(agent_id)

        # Check document exists
        await self._check_document_exists(document_id)

        # Check that requester has ADMIN permission
        has_permission = await self.acl_repo.check_permission(
            document_id, agent_id, "ADMIN"
        )
        if not has_permission:
            raise PermissionDeniedError(
                f"Agent {agent_id} does not have ADMIN permission for document {document_id}"
            )

        # Get all permissions for the document
        permissions = await self.acl_repo.get_by_document(document_id)

        return permissions

    async def set_permissions(
        self,
        document_id: UUID | str,
        permissions: List[dict],
        granted_by: UUID | str,
    ) -> List[DocumentACL]:
        """
        Set permissions for a document (v2.0 unified API).

        v2.0: Bulk permission operation that replaces all existing permissions
        with the provided list. This is more efficient than individual grant/revoke calls.

        Args:
            document_id: Document UUID
            permissions: List of permission dicts:
                {
                    "agent_id": UUID or str,
                    "permission": "READ" | "WRITE" | "DELETE" | "SHARE" | "ADMIN",
                    "expires_at": Optional[datetime]
                }
            granted_by: Agent UUID granting the permissions (must have ADMIN)

        Returns:
            List of updated DocumentACL instances

        Raises:
            DocumentNotFoundError: If document doesn't exist
            AgentNotFoundError: If agent doesn't exist or is invalid
            PermissionDeniedError: If granter lacks ADMIN permission
            ValidationError: If permissions format is invalid
        """
        try:
            # Ensure UUIDs
            document_id = self._ensure_uuid(document_id)
            granted_by = self._ensure_uuid(granted_by)

            # Check agent exists
            await self._check_agent_exists(granted_by)

            # Check document exists
            await self._check_document_exists(document_id)

            # Check that granter has ADMIN permission
            has_permission = await self.acl_repo.check_permission(
                document_id, granted_by, "ADMIN"
            )
            if not has_permission:
                raise PermissionDeniedError(
                    f"Agent {granted_by} does not have ADMIN permission for document {document_id}"
                )

            # Validate all permissions before making changes
            for perm in permissions:
                if "permission" not in perm:
                    raise ValidationError(
                        "Each permission must have 'permission' field"
                    )
                await self._validate_permission(perm["permission"])

                if "agent_id" not in perm:
                    raise ValidationError("Each permission must have 'agent_id' field")
                agent_id = self._ensure_uuid(perm["agent_id"])
                await self._check_agent_exists(agent_id)

            # Use ACL repository's set_permissions method for bulk operation
            result = await self.acl_repo.set_permissions(
                document_id, permissions, granted_by
            )

            logger.info(
                f"Set {len(permissions)} permissions for document {document_id} "
                f"by agent {granted_by}"
            )

            return result

        except (
            DocumentNotFoundError,
            AgentNotFoundError,
            PermissionDeniedError,
            ValidationError,
        ):
            raise
        except Exception as e:
            logger.error(f"Failed to set permissions for document {document_id}: {e}")
            raise ValidationError(f"Failed to set permissions") from e

    async def get_permissions(
        self,
        document_id: UUID | str,
        agent_id: UUID | str,
    ) -> List[DocumentACL]:
        """
        Get all permissions for a document (v2.0 unified API).

        v2.0: Renamed from get_document_permissions for consistency with set_permissions.
        Agent must have ADMIN permission to view all permissions.

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
        # Delegate to existing implementation
        return await self.get_document_permissions(document_id, agent_id)

    # Phase 8: Permissions Refactoring - Consolidated API (v2.0)

    async def set_permissions_bulk(
        self,
        document_id: str | UUID,
        permissions: List[dict],
        granted_by: str | UUID,
    ) -> List[DocumentACL]:
        """
        Set multiple permissions in a single operation (v2.0).

        Consolidated permissions API that replaces share() and revoke().
        Allows setting, updating, or removing permissions in bulk.

        Args:
            document_id: Document UUID
            permissions: List of permission dicts with:
                - agent_id: Agent UUID
                - permission: Permission level (READ, WRITE, DELETE, SHARE, ADMIN)
                - expires_at: Optional expiration datetime (ISO format string or datetime)
                - action: Optional 'remove' to delete permission, default 'grant'
            granted_by: Agent UUID (must have SHARE permission)

        Returns:
            List of updated/created DocumentACL instances

        Raises:
            DocumentNotFoundError: If document doesn't exist
            PermissionDeniedError: If agent lacks SHARE permission
            ValidationError: If permissions are invalid
        """
        from datetime import datetime

        # Convert to UUIDs
        if isinstance(document_id, str):
            document_id = UUID(document_id)
        if isinstance(granted_by, str):
            granted_by = UUID(granted_by)

        # Validate document exists
        doc = await self.document_repo.get_by_id(document_id)
        if not doc:
            raise DocumentNotFoundError(f"Document {document_id} not found")

        # Check SHARE permission
        has_share = await self.acl_repo.check_permission(
            document_id, granted_by, "SHARE"
        )
        if not has_share:
            raise PermissionDeniedError(
                f"Agent {granted_by} does not have SHARE permission for document {document_id}"
            )

        # Validate and process permissions
        valid_permissions = {"READ", "WRITE", "DELETE", "SHARE", "ADMIN"}
        updated_acls = []

        async with self.db_manager.connection() as conn:
            async with conn.transaction():
                for perm_dict in permissions:
                    if "agent_id" not in perm_dict:
                        raise ValidationError("Each permission must have 'agent_id'")

                    agent_id = perm_dict["agent_id"]
                    if isinstance(agent_id, str):
                        agent_id = UUID(agent_id)

                    # Validate agent exists
                    agent = await self.agent_repo.get_by_id(agent_id)
                    if not agent:
                        raise AgentNotFoundError(f"Agent {agent_id} not found")

                    # Check if action is 'remove'
                    action = perm_dict.get("action", "grant")
                    if action == "remove":
                        # Delete permission
                        permission_level = perm_dict.get("permission", "READ")
                        await self.acl_repo.delete_by_document_agent_permission(
                            document_id, agent_id, permission_level
                        )
                        logger.info(
                            f"Removed {permission_level} permission from {agent_id} for document {document_id}"
                        )
                    else:
                        # Grant/update permission
                        if "permission" not in perm_dict:
                            raise ValidationError(
                                "Permission level required: READ, WRITE, DELETE, SHARE, ADMIN"
                            )

                        permission = perm_dict["permission"]
                        if permission not in valid_permissions:
                            raise ValidationError(
                                f"Invalid permission: {permission}. Must be one of {valid_permissions}"
                            )

                        # Parse expiration if provided
                        expires_at = None
                        if "expires_at" in perm_dict and perm_dict["expires_at"]:
                            expires_str = perm_dict["expires_at"]
                            if isinstance(expires_str, str):
                                expires_at = datetime.fromisoformat(expires_str)
                            else:
                                expires_at = expires_str

                        # Delete existing permission if updating
                        await self.acl_repo.delete_by_document_agent_permission(
                            document_id, agent_id, permission
                        )

                        # Create new permission
                        acl_create = DocumentACLCreate(
                            document_id=document_id,
                            agent_id=agent_id,
                            permission=permission,
                            granted_by=granted_by,
                            expires_at=expires_at,
                        )
                        acl = await self.acl_repo.create(acl_create)
                        updated_acls.append(acl)
                        logger.info(
                            f"Set {permission} permission for {agent_id} on document {document_id}"
                        )

        return updated_acls

    async def get_permissions_detailed(
        self, document_id: str | UUID, agent_id: Optional[str | UUID] = None
    ) -> dict:
        """
        Get detailed permission information for a document (v2.0).

        Retrieve all permissions with detailed metadata and filtering options.

        Args:
            document_id: Document UUID
            agent_id: Optional agent UUID to filter permissions for specific agent

        Returns:
            Dictionary with document and its permissions

        Raises:
            DocumentNotFoundError: If document doesn't exist
        """
        if isinstance(document_id, str):
            document_id = UUID(document_id)
        if agent_id and isinstance(agent_id, str):
            agent_id = UUID(agent_id)

        # Validate document exists
        doc = await self.document_repo.get_by_id(document_id)
        if not doc:
            raise DocumentNotFoundError(f"Document {document_id} not found")

        # Get all ACLs
        acls = await self.acl_repo.get_by_document(document_id)

        # Filter by agent if provided
        if agent_id:
            acls = [acl for acl in acls if acl.agent_id == agent_id]

        # Build detailed response
        permissions_list = []
        for acl in acls:
            permissions_list.append(
                {
                    "agent_id": str(acl.agent_id),
                    "permission": acl.permission,
                    "granted_by": str(acl.granted_by),
                    "granted_at": acl.granted_at.isoformat(),
                    "expires_at": (
                        acl.expires_at.isoformat() if acl.expires_at else None
                    ),
                    "is_expired": (
                        acl.expires_at and acl.expires_at < datetime.now()
                        if acl.expires_at
                        else False
                    ),
                }
            )

        return {
            "document_id": str(document_id),
            "document_name": doc.name,
            "total_permissions": len(permissions_list),
            "permissions": permissions_list,
            "agent_filter": str(agent_id) if agent_id else None,
        }

    async def check_permissions_multi(
        self,
        document_id: str | UUID,
        agent_id: str | UUID,
        permissions: List[str],
    ) -> dict:
        """
        Check multiple permissions at once (v2.0).

        Efficiently check if an agent has multiple specific permissions.

        Args:
            document_id: Document UUID
            agent_id: Agent UUID
            permissions: List of permission levels to check

        Returns:
            Dictionary with permission check results

        Raises:
            DocumentNotFoundError: If document doesn't exist
            AgentNotFoundError: If agent doesn't exist
        """
        if isinstance(document_id, str):
            document_id = UUID(document_id)
        if isinstance(agent_id, str):
            agent_id = UUID(agent_id)

        # Validate agent and document exist
        agent = await self.agent_repo.get_by_id(agent_id)
        if not agent:
            raise AgentNotFoundError(f"Agent {agent_id} not found")

        doc = await self.document_repo.get_by_id(document_id)
        if not doc:
            raise DocumentNotFoundError(f"Document {document_id} not found")

        # Check each permission
        results = {}
        for permission in permissions:
            has_perm = await self.acl_repo.check_permission(
                document_id, agent_id, permission
            )
            results[permission] = has_perm

        return {
            "document_id": str(document_id),
            "agent_id": str(agent_id),
            "permissions_checked": results,
            "all_granted": all(results.values()),
            "any_granted": any(results.values()),
        }

    async def transfer_ownership(
        self,
        document_id: str | UUID,
        from_agent_id: str | UUID,
        to_agent_id: str | UUID,
        authorized_by: str | UUID,
    ) -> List[DocumentACL]:
        """
        Transfer document ownership from one agent to another (v2.0).

        Removes ADMIN permission from old owner and grants it to new owner.

        Args:
            document_id: Document UUID
            from_agent_id: Current owner agent UUID
            to_agent_id: New owner agent UUID
            authorized_by: Agent UUID authorizing transfer (must be current owner or admin)

        Returns:
            List of updated ACL entries

        Raises:
            DocumentNotFoundError: If document doesn't exist
            PermissionDeniedError: If not authorized to transfer
        """
        # Convert to UUIDs
        if isinstance(document_id, str):
            document_id = UUID(document_id)
        if isinstance(from_agent_id, str):
            from_agent_id = UUID(from_agent_id)
        if isinstance(to_agent_id, str):
            to_agent_id = UUID(to_agent_id)
        if isinstance(authorized_by, str):
            authorized_by = UUID(authorized_by)

        # Validate document
        doc = await self.document_repo.get_by_id(document_id)
        if not doc:
            raise DocumentNotFoundError(f"Document {document_id} not found")

        # Check authorization
        is_owner = from_agent_id == authorized_by
        is_admin = await self.acl_repo.check_permission(
            document_id, authorized_by, "ADMIN"
        )

        if not (is_owner or is_admin):
            raise PermissionDeniedError(
                f"Agent {authorized_by} is not authorized to transfer ownership"
            )

        # Perform transfer
        async with self.db_manager.connection() as conn:
            async with conn.transaction():
                # Remove ADMIN from old owner
                await self.acl_repo.delete_by_document_agent_permission(
                    document_id, from_agent_id, "ADMIN"
                )

                # Grant ADMIN to new owner
                acl_create = DocumentACLCreate(
                    document_id=document_id,
                    agent_id=to_agent_id,
                    permission="ADMIN",
                    granted_by=authorized_by,
                )
                new_admin = await self.acl_repo.create(acl_create)

                logger.info(
                    f"Transferred ownership of {document_id} from {from_agent_id} to {to_agent_id}"
                )

                return [new_admin]
