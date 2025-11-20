"""
Agent service for DocVault v2.0.

Provides business logic for agent management including registration,
removal, and entity lifecycle management.

v2.0 Changes:
- Agents use external UUIDs as primary keys
- Delete operations with cascade handling
- No name, email, or agent_type fields (managed externally)
- Remove agent functionality with cascade options
"""

import logging
from typing import Optional
from uuid import UUID

from doc_vault.database.postgres_manager import PostgreSQLManager
from doc_vault.database.repositories.acl import ACLRepository
from doc_vault.database.repositories.agent import AgentRepository
from doc_vault.database.repositories.document import DocumentRepository
from doc_vault.database.repositories.organization import OrganizationRepository
from doc_vault.database.schemas.agent import Agent, AgentCreate
from doc_vault.exceptions import (
    AgentNotFoundError,
    DatabaseError,
    OrganizationNotFoundError,
    PermissionDeniedError,
    ValidationError,
)

logger = logging.getLogger(__name__)


class AgentService:
    """
    Service for agent management.

    Orchestrates agent-related operations including registration,
    removal, and entity lifecycle management.

    v2.0: Agents are pure reference entities with only UUID, organization,
    and metadata. Name, email, and agent_type are managed by external systems.
    """

    def __init__(self, db_manager: PostgreSQLManager):
        """
        Initialize the AgentService.

        Args:
            db_manager: Database connection manager
        """
        self.db_manager = db_manager

        # Initialize repositories
        self.agent_repo = AgentRepository(db_manager)
        self.org_repo = OrganizationRepository(db_manager)
        self.document_repo = DocumentRepository(db_manager)
        self.acl_repo = ACLRepository(db_manager)

    def _ensure_uuid(self, value) -> UUID:
        """Convert string UUID to UUID object if needed."""
        if isinstance(value, str):
            return UUID(value)
        return value

    async def register_agent(
        self,
        agent_id: UUID | str,
        organization_id: UUID | str,
        metadata: Optional[dict] = None,
        is_active: bool = True,
    ) -> Agent:
        """
        Register a new agent.

        v2.0: Agent ID is provided by the caller (external system UUID).

        Args:
            agent_id: Agent UUID from external system
            organization_id: Organization UUID this agent belongs to
            metadata: Optional additional metadata (role, department, etc.)
            is_active: Whether the agent is active

        Returns:
            Created Agent instance

        Raises:
            OrganizationNotFoundError: If organization doesn't exist
            ValidationError: If parameters are invalid
            DatabaseError: If creation fails
        """
        try:
            agent_id = self._ensure_uuid(agent_id)
            organization_id = self._ensure_uuid(organization_id)

            # Verify organization exists
            org = await self.org_repo.get_by_id(organization_id)
            if not org:
                raise OrganizationNotFoundError(
                    f"Organization {organization_id} not found"
                )

            # Create agent
            create_data = AgentCreate(
                id=agent_id,
                organization_id=organization_id,
                metadata=metadata or {},
                is_active=is_active,
            )

            agent = await self.agent_repo.create(create_data)

            logger.info(
                f"Registered agent {agent_id} for organization {organization_id}"
            )
            return agent

        except (OrganizationNotFoundError, DatabaseError):
            raise
        except Exception as e:
            logger.error(f"Failed to register agent: {e}")
            raise DatabaseError(f"Failed to register agent") from e

    async def get_agent(self, agent_id: UUID | str) -> Agent:
        """
        Get an agent by UUID.

        Args:
            agent_id: Agent UUID

        Returns:
            Agent instance

        Raises:
            AgentNotFoundError: If agent doesn't exist
        """
        try:
            agent_id = self._ensure_uuid(agent_id)

            agent = await self.agent_repo.get_by_id(agent_id)
            if not agent:
                raise AgentNotFoundError(f"Agent {agent_id} not found")

            return agent

        except AgentNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get agent {agent_id}: {e}")
            raise DatabaseError(f"Failed to get agent") from e

    async def update_agent(
        self,
        agent_id: UUID | str,
        metadata: Optional[dict] = None,
        is_active: Optional[bool] = None,
    ) -> Agent:
        """
        Update an agent's metadata or status.

        Args:
            agent_id: Agent UUID
            metadata: New metadata values
            is_active: New active status

        Returns:
            Updated Agent instance

        Raises:
            AgentNotFoundError: If agent doesn't exist
            DatabaseError: If update fails
        """
        try:
            agent_id = self._ensure_uuid(agent_id)

            # Verify agent exists
            agent = await self.get_agent(agent_id)

            # Build updates
            updates = {}
            if metadata is not None:
                updates["metadata"] = metadata
            if is_active is not None:
                updates["is_active"] = is_active

            if not updates:
                return agent

            updated_agent = await self.agent_repo.update(agent_id, updates)
            if not updated_agent:
                raise AgentNotFoundError(f"Agent {agent_id} not found")

            logger.info(f"Updated agent {agent_id}")
            return updated_agent

        except (AgentNotFoundError, DatabaseError):
            raise
        except Exception as e:
            logger.error(f"Failed to update agent {agent_id}: {e}")
            raise DatabaseError(f"Failed to update agent") from e

    async def remove_agent(
        self,
        agent_id: UUID | str,
        force: bool = False,
        requester_id: Optional[UUID | str] = None,
    ) -> bool:
        """
        Remove an agent from the system.

        v2.0: Agents can be deleted with cascade handling for related documents and ACLs.

        Args:
            agent_id: Agent UUID to remove
            force: If True, cascade delete all related documents and ACLs
                   If False, check first and raise error if related entities exist
            requester_id: Optional UUID of agent requesting removal (for audit)

        Returns:
            True if removed, False if not found

        Raises:
            PermissionDeniedError: If trying to remove with related entities (force=False)
            DatabaseError: If removal fails
        """
        try:
            agent_id = self._ensure_uuid(agent_id)

            logger.info(
                f"Remove agent request: agent_id={agent_id}, force={force}, "
                f"requester={requester_id}"
            )

            # If force=False, check for related entities first
            if not force:
                # Check for documents created by this agent
                docs_created = await self.document_repo.get_by_creator(
                    agent_id, limit=1
                )
                if docs_created:
                    raise PermissionDeniedError(
                        f"Cannot remove agent with {len(docs_created)} document(s) created. "
                        "Use force=True to cascade delete."
                    )

                # Check for ACLs involving this agent
                acls = await self.acl_repo.get_by_agent(agent_id, limit=1)
                if acls:
                    raise PermissionDeniedError(
                        f"Cannot remove agent with {len(acls)} permission grant(s). "
                        "Use force=True to cascade delete."
                    )

            # Delete agent
            result = await self.agent_repo.delete(agent_id, force=force)

            if result:
                logger.info(f"Removed agent {agent_id}")
            else:
                logger.warning(f"Agent {agent_id} not found for removal")

            return result

        except (PermissionDeniedError, DatabaseError):
            raise
        except Exception as e:
            logger.error(f"Failed to remove agent {agent_id}: {e}")
            raise DatabaseError(f"Failed to remove agent") from e

    async def remove_from_organization(
        self,
        agent_id: UUID | str,
        requester_id: Optional[UUID | str] = None,
    ) -> bool:
        """
        Soft remove an agent from an organization (mark as inactive).

        This is a gentler approach than hard delete - the agent record remains
        but is marked as inactive.

        Args:
            agent_id: Agent UUID to remove from organization
            requester_id: Optional UUID of agent requesting removal (for audit)

        Returns:
            True if removed, False if not found

        Raises:
            AgentNotFoundError: If agent doesn't exist
            DatabaseError: If operation fails
        """
        try:
            agent_id = self._ensure_uuid(agent_id)

            logger.info(
                f"Soft remove agent from organization: agent_id={agent_id}, "
                f"requester={requester_id}"
            )

            # Mark agent as inactive
            updated_agent = await self.update_agent(agent_id, is_active=False)

            if updated_agent:
                logger.info(f"Soft removed agent {agent_id} from organization")
                return True
            else:
                logger.warning(f"Agent {agent_id} not found")
                return False

        except Exception as e:
            logger.error(f"Failed to remove agent {agent_id} from organization: {e}")
            raise DatabaseError(f"Failed to remove agent from organization") from e

    async def get_organization_agents(
        self,
        organization_id: UUID | str,
        active_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Agent]:
        """
        List agents in an organization.

        Args:
            organization_id: Organization UUID
            active_only: If True, return only active agents
            limit: Maximum number of agents to return
            offset: Number of agents to skip

        Returns:
            List of Agent instances

        Raises:
            OrganizationNotFoundError: If organization doesn't exist
            ValidationError: If parameters are invalid
            DatabaseError: If listing fails
        """
        try:
            organization_id = self._ensure_uuid(organization_id)

            # Verify organization exists
            org = await self.org_repo.get_by_id(organization_id)
            if not org:
                raise OrganizationNotFoundError(
                    f"Organization {organization_id} not found"
                )

            if limit < 1 or limit > 1000:
                raise ValidationError("limit must be between 1 and 1000")
            if offset < 0:
                raise ValidationError("offset must be >= 0")

            if active_only:
                agents = await self.agent_repo.get_active_by_organization(
                    organization_id, limit=limit, offset=offset
                )
            else:
                agents = await self.agent_repo.get_by_organization(
                    organization_id, limit=limit, offset=offset
                )

            return agents

        except (OrganizationNotFoundError, ValidationError, DatabaseError):
            raise
        except Exception as e:
            logger.error(f"Failed to get organization agents: {e}")
            raise DatabaseError(f"Failed to get organization agents") from e
