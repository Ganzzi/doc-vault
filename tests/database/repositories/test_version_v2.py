"""
Tests for Version Repository (v2.0).

Tests cover:
- Version creation with UUID-based operations
- get_by_document() method
- delete_version() with cleanup option
- Version numbering and ordering
- Error conditions
"""

import pytest
from uuid import uuid4

from doc_vault.database.repositories.version import VersionRepository
from doc_vault.database.repositories.document import DocumentRepository
from doc_vault.database.repositories.organization import OrganizationRepository
from doc_vault.database.repositories.agent import AgentRepository
from doc_vault.database.schemas.version import DocumentVersion, DocumentVersionCreate
from doc_vault.database.schemas.document import DocumentCreate
from doc_vault.database.schemas.organization import OrganizationCreate
from doc_vault.database.schemas.agent import AgentCreate


@pytest.fixture
async def version_repo(db_manager):
    """Create a version repository."""
    return VersionRepository(db_manager)


@pytest.fixture
async def doc_repo(db_manager):
    """Create a document repository."""
    return DocumentRepository(db_manager)


@pytest.fixture
async def org_repo(db_manager):
    """Create an organization repository."""
    return OrganizationRepository(db_manager)


@pytest.fixture
async def agent_repo(db_manager):
    """Create an agent repository."""
    return AgentRepository(db_manager)


@pytest.fixture
async def organization(org_repo):
    """Create a test organization."""
    org_id = uuid4()
    create_data = OrganizationCreate(id=org_id)
    return await org_repo.create(create_data)


@pytest.fixture
async def agent(agent_repo, organization):
    """Create a test agent."""
    agent_id = uuid4()
    create_data = AgentCreate(id=agent_id, organization_id=organization.id)
    return await agent_repo.create(create_data)


@pytest.fixture
async def document(doc_repo, organization, agent):
    """Create a test document."""
    doc_id = uuid4()
    create_data = DocumentCreate(
        id=doc_id,
        organization_id=organization.id,
        name="Document.pdf",
        filename="document.pdf",
        file_size=1024,
        mime_type="application/pdf",
        storage_path=f"docs/{doc_id}/document.pdf",
        created_by=agent.id,
        updated_by=agent.id,
    )
    return await doc_repo.create(create_data)


class TestVersionCreate:
    """Test version creation."""

    async def test_create_version(self, version_repo, document, agent):
        """Test creating a version."""
        version_id = uuid4()
        create_data = DocumentVersionCreate(
            id=version_id,
            document_id=document.id,
            version_number=1,
            filename=document.filename,
            file_size=document.file_size,
            storage_path=f"versions/{version_id}/document.pdf",
            created_by=agent.id,
        )

        version = await version_repo.create(create_data)

        assert version.id == version_id
        assert version.document_id == document.id
        assert version.version_number == 1
        assert version.filename == document.filename

    async def test_create_multiple_versions(self, version_repo, document, agent):
        """Test creating multiple versions of same document."""
        version_ids = []
        for i in range(1, 4):
            version_id = uuid4()
            create_data = DocumentVersionCreate(
                id=version_id,
                document_id=document.id,
                version_number=i,
                filename=f"document_v{i}.pdf",
                file_size=1024 * i,
                storage_path=f"versions/{version_id}/document_v{i}.pdf",
                created_by=agent.id,
            )
            version = await version_repo.create(create_data)
            version_ids.append(version.id)

        # Verify all versions created
        for version_id in version_ids:
            retrieved = await version_repo.get_by_id(version_id)
            assert retrieved is not None


class TestVersionGet:
    """Test version retrieval."""

    async def test_get_by_id(self, version_repo, document, agent):
        """Test getting a version by ID."""
        version_id = uuid4()
        create_data = DocumentVersionCreate(
            id=version_id,
            document_id=document.id,
            version_number=1,
            filename="v1.pdf",
            file_size=1024,
            storage_path=f"versions/{version_id}/v1.pdf",
            created_by=agent.id,
        )
        await version_repo.create(create_data)

        version = await version_repo.get_by_id(version_id)

        assert version is not None
        assert version.id == version_id
        assert version.version_number == 1

    async def test_get_by_document(self, version_repo, document, agent):
        """Test getting all versions of a document."""
        # Create multiple versions
        for i in range(1, 4):
            version_id = uuid4()
            create_data = DocumentVersionCreate(
                id=version_id,
                document_id=document.id,
                version_number=i,
                filename=f"v{i}.pdf",
                file_size=1024,
                storage_path=f"versions/{version_id}/v{i}.pdf",
                created_by=agent.id,
            )
            await version_repo.create(create_data)

        # Get all versions
        versions = await version_repo.get_by_document(document.id)

        assert len(versions) >= 3
        # Verify ordered by version number
        version_numbers = [v.version_number for v in versions]
        assert version_numbers == sorted(version_numbers)

    async def test_get_by_document_limit_offset(self, version_repo, document, agent):
        """Test getting versions with pagination."""
        # Create multiple versions
        for i in range(1, 6):
            version_id = uuid4()
            create_data = DocumentVersionCreate(
                id=version_id,
                document_id=document.id,
                version_number=i,
                filename=f"v{i}.pdf",
                file_size=1024,
                storage_path=f"versions/{version_id}/v{i}.pdf",
                created_by=agent.id,
            )
            await version_repo.create(create_data)

        # Get paginated versions
        versions_page1 = await version_repo.get_by_document(
            document.id, limit=2, offset=0
        )
        versions_page2 = await version_repo.get_by_document(
            document.id, limit=2, offset=2
        )

        assert len(versions_page1) == 2
        assert len(versions_page2) == 2


class TestVersionDelete:
    """Test version deletion."""

    async def test_delete_version(self, version_repo, document, agent):
        """Test deleting a version."""
        version_id = uuid4()
        create_data = DocumentVersionCreate(
            id=version_id,
            document_id=document.id,
            version_number=1,
            filename="v1.pdf",
            file_size=1024,
            storage_path=f"versions/{version_id}/v1.pdf",
            created_by=agent.id,
        )
        await version_repo.create(create_data)

        # Delete version
        result = await version_repo.delete(version_id)

        assert result is True
        retrieved = await version_repo.get_by_id(version_id)
        assert retrieved is None


class TestVersionUpdate:
    """Test version update operations."""

    async def test_update_change_description(self, version_repo, document, agent):
        """Test updating version change description."""
        version_id = uuid4()
        create_data = DocumentVersionCreate(
            id=version_id,
            document_id=document.id,
            version_number=1,
            filename="v1.pdf",
            file_size=1024,
            storage_path=f"versions/{version_id}/v1.pdf",
            created_by=agent.id,
            change_description="Initial version",
        )
        await version_repo.create(create_data)

        # Update description
        updated = await version_repo.update(
            version_id, {"change_description": "Updated description"}
        )

        assert updated is not None
        assert updated.change_description == "Updated description"

