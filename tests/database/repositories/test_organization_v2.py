"""
Tests for Organization Repository (v2.0).

Tests cover:
- UUID-based create operations
- UUID-based get operations
- Delete operations with cascade checks
- Metadata handling
- Error conditions
"""

import pytest
from uuid import UUID, uuid4

from doc_vault.database.repositories.organization import OrganizationRepository
from doc_vault.database.schemas.organization import Organization, OrganizationCreate
from doc_vault.exceptions import DatabaseError


@pytest.fixture
async def org_repo(db_manager):
    """Create an organization repository."""
    return OrganizationRepository(db_manager)


class TestOrganizationCreate:
    """Test organization creation with v2.0 UUID-based approach."""

    async def test_create_organization(self, org_repo):
        """Test creating an organization with external UUID."""
        org_id = uuid4()
        create_data = OrganizationCreate(id=org_id, metadata={"plan": "premium"})

        org = await org_repo.create(create_data)

        assert org.id == org_id
        assert org.metadata == {"plan": "premium"}
        assert org.created_at is not None
        assert org.updated_at is not None

    async def test_create_organization_minimal(self, org_repo):
        """Test creating an organization with minimal data."""
        org_id = uuid4()
        create_data = OrganizationCreate(id=org_id)

        org = await org_repo.create(create_data)

        assert org.id == org_id
        assert org.metadata == {}

    async def test_create_organization_with_metadata(self, org_repo):
        """Test creating an organization with various metadata."""
        org_id = uuid4()
        metadata = {
            "plan": "enterprise",
            "seats": 100,
            "features": ["advanced_search", "custom_branding"],
            "billing_email": "billing@company.com",
        }
        create_data = OrganizationCreate(id=org_id, metadata=metadata)

        org = await org_repo.create(create_data)

        assert org.metadata == metadata


class TestOrganizationGet:
    """Test organization retrieval operations."""

    async def test_get_by_id(self, org_repo):
        """Test getting an organization by UUID."""
        org_id = uuid4()
        create_data = OrganizationCreate(id=org_id, metadata={"tier": "basic"})
        created = await org_repo.create(create_data)

        retrieved = await org_repo.get_by_id(org_id)

        assert retrieved is not None
        assert retrieved.id == org_id
        assert retrieved.metadata == {"tier": "basic"}

    async def test_get_by_id_string(self, org_repo):
        """Test getting an organization using string UUID."""
        org_id = uuid4()
        create_data = OrganizationCreate(id=org_id)
        await org_repo.create(create_data)

        # Pass UUID as string
        retrieved = await org_repo.get_by_id(str(org_id))

        assert retrieved is not None
        assert retrieved.id == org_id

    async def test_get_by_id_not_found(self, org_repo):
        """Test getting non-existent organization returns None."""
        non_existent_id = uuid4()

        result = await org_repo.get_by_id(non_existent_id)

        assert result is None

    async def test_list_organizations(self, org_repo):
        """Test listing organizations."""
        # Create multiple organizations
        org_ids = [uuid4(), uuid4(), uuid4()]
        for org_id in org_ids:
            create_data = OrganizationCreate(id=org_id)
            await org_repo.create(create_data)

        # List organizations
        orgs = await org_repo.list(limit=10)

        assert len(orgs) >= 3
        retrieved_ids = [org.id for org in orgs]
        for org_id in org_ids:
            assert org_id in retrieved_ids


class TestOrganizationDelete:
    """Test organization deletion operations."""

    async def test_delete_empty_organization(self, org_repo, agent_repo):
        """Test deleting an organization without agents."""
        org_id = uuid4()
        create_data = OrganizationCreate(id=org_id)
        await org_repo.create(create_data)

        # Delete should succeed (no related entities)
        result = await org_repo.delete(org_id, force=False)

        assert result is True
        retrieved = await org_repo.get_by_id(org_id)
        assert retrieved is None

    async def test_delete_organization_with_agents_without_force(
        self, org_repo, agent_repo
    ):
        """Test that delete fails with agents if force=False."""
        # Create organization
        org_id = uuid4()
        org_create = OrganizationCreate(id=org_id)
        await org_repo.create(org_create)

        # Create agent for this organization
        agent_id = uuid4()
        from doc_vault.database.schemas.agent import AgentCreate

        agent_create = AgentCreate(id=agent_id, organization_id=org_id)
        await agent_repo.create(agent_create)

        # Delete should fail without force
        with pytest.raises(DatabaseError) as exc_info:
            await org_repo.delete(org_id, force=False)

        assert "Cannot delete organization" in str(exc_info.value)

    async def test_delete_organization_with_agents_with_force(
        self, org_repo, agent_repo
    ):
        """Test that delete succeeds with agents if force=True."""
        # Create organization
        org_id = uuid4()
        org_create = OrganizationCreate(id=org_id)
        await org_repo.create(org_create)

        # Create agent for this organization
        agent_id = uuid4()
        from doc_vault.database.schemas.agent import AgentCreate

        agent_create = AgentCreate(id=agent_id, organization_id=org_id)
        await agent_repo.create(agent_create)

        # Delete should succeed with force=True
        result = await org_repo.delete(org_id, force=True)

        assert result is True
        retrieved = await org_repo.get_by_id(org_id)
        assert retrieved is None

    async def test_delete_non_existent_organization(self, org_repo):
        """Test deleting non-existent organization returns False."""
        result = await org_repo.delete(uuid4())

        assert result is False

    async def test_delete_with_string_uuid(self, org_repo):
        """Test delete with string UUID."""
        org_id = uuid4()
        create_data = OrganizationCreate(id=org_id)
        await org_repo.create(create_data)

        # Delete using string UUID
        result = await org_repo.delete(str(org_id))

        assert result is True


class TestOrganizationUpdate:
    """Test organization update operations."""

    async def test_update_metadata(self, org_repo):
        """Test updating organization metadata."""
        org_id = uuid4()
        create_data = OrganizationCreate(id=org_id, metadata={"plan": "basic"})
        await org_repo.create(create_data)

        # Update metadata
        updated_org = await org_repo.update(org_id, {"metadata": {"plan": "premium"}})

        assert updated_org is not None
        assert updated_org.metadata == {"plan": "premium"}

    async def test_update_nonexistent_organization(self, org_repo):
        """Test updating non-existent organization returns None."""
        result = await org_repo.update(uuid4(), {"metadata": {"plan": "basic"}})

        assert result is None


class TestOrganizationErrors:
    """Test error handling."""

    async def test_create_duplicate_id(self, org_repo):
        """Test that creating organization with same ID fails."""
        org_id = uuid4()
        create_data = OrganizationCreate(id=org_id)
        await org_repo.create(create_data)

        # Try to create another with same ID
        with pytest.raises(Exception):  # Database error due to unique constraint
            await org_repo.create(create_data)

    async def test_invalid_uuid_string(self, org_repo):
        """Test that invalid UUID string raises error."""
        with pytest.raises(ValueError):
            await org_repo.get_by_id("not-a-uuid")

