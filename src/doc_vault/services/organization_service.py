"""
Organization service for DocVault v2.0.

Provides business logic for organization management including creation,
deletion, and entity management operations.

v2.0 Changes:
- Organizations use external UUIDs as primary keys
- Delete operations with cascade handling
- No name or external_id fields (managed externally)
"""

import logging
from typing import Optional
from uuid import UUID

from doc_vault.database.postgres_manager import PostgreSQLManager
from doc_vault.database.repositories.agent import AgentRepository
from doc_vault.database.repositories.document import DocumentRepository
from doc_vault.database.repositories.organization import OrganizationRepository
from doc_vault.database.schemas.organization import Organization, OrganizationCreate
from doc_vault.exceptions import (
    DatabaseError,
    OrganizationNotFoundError,
    PermissionDeniedError,
    ValidationError,
)

logger = logging.getLogger(__name__)


class OrganizationService:
    """
    Service for organization management.

    Orchestrates organization-related operations including registration,
    deletion, and entity lifecycle management.

    v2.0: Organizations are pure reference entities with only UUID and metadata.
    Name, billing info, and other details are managed by external systems.
    """

    def __init__(self, db_manager: PostgreSQLManager):
        """
        Initialize the OrganizationService.

        Args:
            db_manager: Database connection manager
        """
        self.db_manager = db_manager

        # Initialize repositories
        self.org_repo = OrganizationRepository(db_manager)
        self.agent_repo = AgentRepository(db_manager)
        self.document_repo = DocumentRepository(db_manager)

    def _ensure_uuid(self, value) -> UUID:
        """Convert string UUID to UUID object if needed."""
        if isinstance(value, str):
            return UUID(value)
        return value

    async def register_organization(
        self,
        org_id: UUID | str,
        metadata: Optional[dict] = None,
    ) -> Organization:
        """
        Register a new organization.

        v2.0: Organization ID is provided by the caller (external system UUID).

        Args:
            org_id: Organization UUID from external system
            metadata: Optional additional metadata (plan, billing info, etc.)

        Returns:
            Created Organization instance

        Raises:
            ValidationError: If parameters are invalid
            DatabaseError: If creation fails
        """
        try:
            org_id = self._ensure_uuid(org_id)

            # Create organization
            create_data = OrganizationCreate(
                id=org_id,
                metadata=metadata or {},
            )

            org = await self.org_repo.create(create_data)

            logger.info(f"Registered organization {org_id}")
            return org

        except Exception as e:
            logger.error(f"Failed to register organization: {e}")
            raise

    async def get_organization(self, org_id: UUID | str) -> Organization:
        """
        Get an organization by UUID.

        Args:
            org_id: Organization UUID

        Returns:
            Organization instance

        Raises:
            OrganizationNotFoundError: If organization doesn't exist
        """
        try:
            org_id = self._ensure_uuid(org_id)

            org = await self.org_repo.get_by_id(org_id)
            if not org:
                raise OrganizationNotFoundError(f"Organization {org_id} not found")

            return org

        except OrganizationNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get organization {org_id}: {e}")
            raise DatabaseError("Failed to get organization") from e

    async def update_organization(
        self,
        org_id: UUID | str,
        metadata: Optional[dict] = None,
    ) -> Organization:
        """
        Update an organization's metadata.

        Args:
            org_id: Organization UUID
            metadata: New metadata values

        Returns:
            Updated Organization instance

        Raises:
            OrganizationNotFoundError: If organization doesn't exist
            DatabaseError: If update fails
        """
        try:
            org_id = self._ensure_uuid(org_id)

            # Verify organization exists
            org = await self.get_organization(org_id)

            # Update only metadata
            updates = {}
            if metadata is not None:
                updates["metadata"] = metadata

            if not updates:
                return org

            updated_org = await self.org_repo.update(org_id, updates)
            if not updated_org:
                raise OrganizationNotFoundError(f"Organization {org_id} not found")

            logger.info(f"Updated organization {org_id}")
            return updated_org

        except (OrganizationNotFoundError, DatabaseError):
            raise
        except Exception as e:
            logger.error(f"Failed to update organization {org_id}: {e}")
            raise DatabaseError("Failed to update organization") from e

    async def delete_organization(
        self,
        org_id: UUID | str,
        force: bool = False,
        requester_id: Optional[UUID | str] = None,
    ) -> bool:
        """
        Delete an organization.

        v2.0: Organizations can cascade-delete their related entities.

        Args:
            org_id: Organization UUID to delete
            force: If True, cascade delete all related agents and documents
                   If False, check first and raise error if related entities exist
            requester_id: Optional UUID of agent requesting deletion (for audit)

        Returns:
            True if deleted, False if not found

        Raises:
            PermissionDeniedError: If trying to delete with related entities (force=False)
            DatabaseError: If deletion fails
        """
        try:
            org_id = self._ensure_uuid(org_id)

            logger.info(
                f"Delete organization request: org_id={org_id}, force={force}, "
                f"requester={requester_id}"
            )

            # If force=False, check for related entities first
            if not force:
                # Count agents
                agents = await self.agent_repo.get_by_organization(org_id, limit=1)
                if agents:
                    raise PermissionDeniedError(
                        f"Cannot delete organization with {len(agents)} agent(s). "
                        "Use force=True to cascade delete."
                    )

                # Count documents
                docs = await self.document_repo.get_by_organization(org_id, limit=1)
                if docs:
                    raise PermissionDeniedError(
                        f"Cannot delete organization with {len(docs)} document(s). "
                        "Use force=True to cascade delete."
                    )

            # Delete organization
            result = await self.org_repo.delete(org_id, force=force)

            if result:
                logger.info(f"Deleted organization {org_id}")
            else:
                logger.warning(f"Organization {org_id} not found for deletion")

            return result

        except (PermissionDeniedError, DatabaseError):
            raise
        except Exception as e:
            logger.error(f"Failed to delete organization {org_id}: {e}")
            raise DatabaseError("Failed to delete organization") from e

    async def list_organizations(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Organization]:
        """
        List all organizations with pagination.

        Args:
            limit: Maximum number of organizations to return
            offset: Number of organizations to skip

        Returns:
            List of Organization instances

        Raises:
            ValidationError: If parameters are invalid
            DatabaseError: If listing fails
        """
        try:
            if limit < 1 or limit > 1000:
                raise ValidationError("limit must be between 1 and 1000")
            if offset < 0:
                raise ValidationError("offset must be >= 0")

            orgs = await self.org_repo.list(limit=limit, offset=offset)
            return orgs

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to list organizations: {e}")
            raise DatabaseError("Failed to list organizations") from e
