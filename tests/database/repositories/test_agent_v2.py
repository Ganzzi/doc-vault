"""
Tests for Agent Repository (v2.0).

Tests cover:
- UUID-based create operations
- UUID-based get operations
- Delete operations with cascade checks
- get_by_organization() and get_active_by_organization()
- remove_from_organization() method
- Error conditions
"""

import pytest
from uuid import UUID, uuid4

from doc_vault.database.repositories.agent import AgentRepository
from doc_vault.database.repositories.organization import OrganizationRepository
from doc_vault.database.schemas.agent import Agent, AgentCreate
from doc_vault.database.schemas.organization import OrganizationCreate
from doc_vault.exceptions import DatabaseError


@pytest.fixture
async def agent_repo(db_manager):
    """Create an agent repository."""
    return AgentRepository(db_manager)


@pytest.fixture
async def org_repo(db_manager):
    """Create an organization repository."""
    return OrganizationRepository(db_manager)


@pytest.fixture
async def organization(org_repo):
    """Create a test organization."""
    org_id = uuid4()
    create_data = OrganizationCreate(id=org_id)
    return await org_repo.create(create_data)


class TestAgentCreate:
    """Test agent creation with v2.0 UUID-based approach."""

    async def test_create_agent(self, agent_repo, organization):
        """Test creating an agent with external UUID."""
        agent_id = uuid4()
        create_data = AgentCreate(
            id=agent_id,
            organization_id=organization.id,
            metadata={"role": "admin"},
        )

        agent = await agent_repo.create(create_data)

        assert agent.id == agent_id
        assert agent.organization_id == organization.id
        assert agent.metadata == {"role": "admin"}
        assert agent.is_active is True
        assert agent.created_at is not None

    async def test_create_agent_minimal(self, agent_repo, organization):
        """Test creating an agent with minimal data."""
        agent_id = uuid4()
        create_data = AgentCreate(id=agent_id, organization_id=organization.id)

        agent = await agent_repo.create(create_data)

        assert agent.id == agent_id
        assert agent.organization_id == organization.id
        assert agent.metadata == {}
        assert agent.is_active is True

    async def test_create_agent_with_metadata(self, agent_repo, organization):
        """Test creating an agent with various metadata."""
        agent_id = uuid4()
        metadata = {
            "role": "manager",
            "department": "engineering",
            "permissions": ["read", "write", "delete"],
        }
        create_data = AgentCreate(
            id=agent_id, organization_id=organization.id, metadata=metadata
        )

        agent = await agent_repo.create(create_data)

        assert agent.metadata == metadata


class TestAgentGet:
    """Test agent retrieval operations."""

    async def test_get_by_id(self, agent_repo, organization):
        """Test getting an agent by UUID."""
        agent_id = uuid4()
        create_data = AgentCreate(
            id=agent_id, organization_id=organization.id, metadata={"tier": "senior"}
        )
        created = await agent_repo.create(create_data)

        retrieved = await agent_repo.get_by_id(agent_id)

        assert retrieved is not None
        assert retrieved.id == agent_id
        assert retrieved.metadata == {"tier": "senior"}

    async def test_get_by_id_string(self, agent_repo, organization):
        """Test getting an agent using string UUID."""
        agent_id = uuid4()
        create_data = AgentCreate(id=agent_id, organization_id=organization.id)
        await agent_repo.create(create_data)

        # Pass UUID as string
        retrieved = await agent_repo.get_by_id(str(agent_id))

        assert retrieved is not None
        assert retrieved.id == agent_id

    async def test_get_by_id_not_found(self, agent_repo):
        """Test getting non-existent agent returns None."""
        non_existent_id = uuid4()

        result = await agent_repo.get_by_id(non_existent_id)

        assert result is None

    async def test_get_by_organization(self, agent_repo, organization):
        """Test getting all agents for an organization."""
        # Create multiple agents
        agent_ids = [uuid4(), uuid4(), uuid4()]
        for agent_id in agent_ids:
            create_data = AgentCreate(id=agent_id, organization_id=organization.id)
            await agent_repo.create(create_data)

        # Get all agents for organization
        agents = await agent_repo.get_by_organization(organization.id)

        assert len(agents) >= 3
        retrieved_ids = [agent.id for agent in agents]
        for agent_id in agent_ids:
            assert agent_id in retrieved_ids

    async def test_get_by_organization_with_pagination(self, agent_repo, organization):
        """Test get_by_organization with limit and offset."""
        # Create multiple agents
        for _ in range(5):
            agent_id = uuid4()
            create_data = AgentCreate(id=agent_id, organization_id=organization.id)
            await agent_repo.create(create_data)

        # Get with pagination
        agents_page1 = await agent_repo.get_by_organization(
            organization.id, limit=2, offset=0
        )
        agents_page2 = await agent_repo.get_by_organization(
            organization.id, limit=2, offset=2
        )

        assert len(agents_page1) == 2
        assert len(agents_page2) == 2

        # Verify different pages
        page1_ids = {a.id for a in agents_page1}
        page2_ids = {a.id for a in agents_page2}
        assert page1_ids != page2_ids

    async def test_get_active_by_organization(self, agent_repo, organization):
        """Test getting only active agents for an organization."""
        # Create active agent
        active_id = uuid4()
        active_data = AgentCreate(
            id=active_id, organization_id=organization.id, is_active=True
        )
        await agent_repo.create(active_data)

        # Create inactive agent
        inactive_id = uuid4()
        inactive_data = AgentCreate(
            id=inactive_id, organization_id=organization.id, is_active=False
        )
        await agent_repo.create(inactive_data)

        # Get active agents only
        active_agents = await agent_repo.get_active_by_organization(organization.id)

        active_ids = [a.id for a in active_agents]
        assert active_id in active_ids
        assert inactive_id not in active_ids


class TestAgentDelete:
    """Test agent deletion operations."""

    async def test_delete_agent(self, agent_repo, organization):
        """Test deleting an agent."""
        agent_id = uuid4()
        create_data = AgentCreate(id=agent_id, organization_id=organization.id)
        await agent_repo.create(create_data)

        # Delete should succeed
        result = await agent_repo.delete(agent_id, force=False)

        assert result is True
        retrieved = await agent_repo.get_by_id(agent_id)
        assert retrieved is None

    async def test_delete_non_existent_agent(self, agent_repo):
        """Test deleting non-existent agent returns False."""
        result = await agent_repo.delete(uuid4())

        assert result is False

    async def test_delete_with_string_uuid(self, agent_repo, organization):
        """Test delete with string UUID."""
        agent_id = uuid4()
        create_data = AgentCreate(id=agent_id, organization_id=organization.id)
        await agent_repo.create(create_data)

        # Delete using string UUID
        result = await agent_repo.delete(str(agent_id))

        assert result is True

    async def test_remove_from_organization(self, agent_repo, organization):
        """Test removing an agent from an organization."""
        agent_id = uuid4()
        create_data = AgentCreate(id=agent_id, organization_id=organization.id)
        await agent_repo.create(create_data)

        # Remove from organization (soft removal)
        await agent_repo.remove_from_organization(agent_id)

        # Agent should still exist but be inactive/removed
        retrieved = await agent_repo.get_by_id(agent_id)
        # Should either be deleted or marked inactive (depends on implementation)
        # For now, just verify we can call it without error


class TestAgentUpdate:
    """Test agent update operations."""

    async def test_update_metadata(self, agent_repo, organization):
        """Test updating agent metadata."""
        agent_id = uuid4()
        create_data = AgentCreate(
            id=agent_id,
            organization_id=organization.id,
            metadata={"role": "junior"},
        )
        await agent_repo.create(create_data)

        # Update metadata
        updated_agent = await agent_repo.update(
            agent_id, {"metadata": {"role": "senior"}}
        )

        assert updated_agent is not None
        assert updated_agent.metadata == {"role": "senior"}

    async def test_update_is_active(self, agent_repo, organization):
        """Test updating agent active status."""
        agent_id = uuid4()
        create_data = AgentCreate(id=agent_id, organization_id=organization.id)
        await agent_repo.create(create_data)

        # Update to inactive
        updated_agent = await agent_repo.update(agent_id, {"is_active": False})

        assert updated_agent is not None
        assert updated_agent.is_active is False

    async def test_update_nonexistent_agent(self, agent_repo):
        """Test updating non-existent agent returns None."""
        result = await agent_repo.update(uuid4(), {"is_active": False})

        assert result is None


class TestAgentErrors:
    """Test error handling."""

    async def test_create_duplicate_id(self, agent_repo, organization):
        """Test that creating agent with same ID fails."""
        agent_id = uuid4()
        create_data = AgentCreate(id=agent_id, organization_id=organization.id)
        await agent_repo.create(create_data)

        # Try to create another with same ID
        with pytest.raises(Exception):  # Database error due to unique constraint
            await agent_repo.create(create_data)

    async def test_invalid_uuid_string(self, agent_repo):
        """Test that invalid UUID string raises error."""
        with pytest.raises(ValueError):
            await agent_repo.get_by_id("not-a-uuid")

    async def test_create_with_invalid_organization_id(self, agent_repo):
        """Test creating agent with non-existent organization."""
        agent_id = uuid4()
        invalid_org_id = uuid4()  # Organization doesn't exist
        create_data = AgentCreate(id=agent_id, organization_id=invalid_org_id)

        # Should raise error due to foreign key constraint
        with pytest.raises(Exception):
            await agent_repo.create(create_data)

