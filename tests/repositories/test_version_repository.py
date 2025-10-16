"""
Tests for Version repository.

This module tests the VersionRepositor        # Create version
        version = await version_repo.create_from_create_schema(version_create)
        assert version.document_id == doc.id
        assert version.version_number == 1
        assert version.filename == "test.pdf"
        assert version.change_type == "create"

        # Get by ID
        retrieved = await version_repo.get_by_id(version.id)ethods.
"""

import pytest
from uuid import uuid4

from doc_vault.database.repositories.version import VersionRepository
from doc_vault.database.repositories.document import DocumentRepository
from doc_vault.database.repositories.organization import OrganizationRepository
from doc_vault.database.repositories.agent import AgentRepository
from doc_vault.database.schemas.version import DocumentVersionCreate
from doc_vault.database.schemas.document import DocumentCreate
from doc_vault.database.schemas.organization import OrganizationCreate
from doc_vault.database.schemas.agent import AgentCreate


class TestVersionRepository:
    """Test Version repository operations."""

    @pytest.mark.asyncio
    async def test_create_and_get_version(self, db_manager):
        """Test creating and retrieving document versions."""
        # Create prerequisite repositories
        org_repo = OrganizationRepository(db_manager)
        agent_repo = AgentRepository(db_manager)
        doc_repo = DocumentRepository(db_manager)
        version_repo = VersionRepository(db_manager)

        # Create organization
        org_external_id = f"test-org-version-{uuid4()}"
        org_create = OrganizationCreate(
            external_id=org_external_id,
            name="Test Organization for Version",
        )
        org = await org_repo.create_from_create_schema(org_create)

        # Create agent
        agent_external_id = f"test-agent-version-{uuid4()}"
        agent_create = AgentCreate(
            external_id=agent_external_id,
            organization_id=str(org.id),
            name="Test Agent for Version",
        )
        agent = await agent_repo.create_from_create_schema(agent_create)

        # Create document
        doc_create = DocumentCreate(
            organization_id=org.id,
            name="Test Document for Version",
            filename="test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            storage_path="test/path/test.pdf",
            created_by=agent.id,
            description="Test document for version",
            tags=["test"],
            metadata={"test": True},
        )
        doc = await doc_repo.create_from_create_schema(doc_create)

        version_create = DocumentVersionCreate(
            document_id=doc.id,
            version_number=1,
            filename="test.pdf",
            file_size=1024,
            storage_path="test/path/v1/test.pdf",
            mime_type="application/pdf",
            change_description="Initial version",
            change_type="create",
            created_by=agent.id,
            metadata={"version": "1.0"},
        )

        # Create version
        version = await version_repo.create_from_create_schema(version_create)
        assert version.document_id == doc.id
        assert version.version_number == 1
        assert version.filename == "test.pdf"
        assert version.change_type == "create"

        # Get by ID
        retrieved = await version_repo.get_by_id(version.id)
        assert retrieved.id == version.id
        assert retrieved.version_number == 1

    @pytest.mark.asyncio
    async def test_get_by_document(self, db_manager):
        """Test getting versions by document."""
        repo = VersionRepository(db_manager)

        # Create prerequisite entities
        org_repo = OrganizationRepository(db_manager)
        agent_repo = AgentRepository(db_manager)
        doc_repo = DocumentRepository(db_manager)

        # Create organization
        org_external_id = f"test-org-version-get-by-doc-{uuid4()}"
        org_create = OrganizationCreate(
            name="Test Organization", external_id=org_external_id
        )
        org = await org_repo.create_from_create_schema(org_create)

        # Create agent
        agent_external_id = f"test-agent-version-get-by-doc-{uuid4()}"
        agent_create = AgentCreate(
            organization_id=org.id, name="Test Agent", external_id=agent_external_id
        )
        agent = await agent_repo.create_from_create_schema(agent_create)

        # Create document
        doc_create = DocumentCreate(
            organization_id=org.id,
            name="Test Document for Versions",
            filename="test.pdf",
            file_size=1024,
            storage_path="test/path/test.pdf",
            created_by=agent.id,
        )
        doc = await doc_repo.create_from_create_schema(doc_create)

        # Create multiple versions
        for version_num in [1, 2, 3]:
            version_create = DocumentVersionCreate(
                document_id=doc.id,
                version_number=version_num,
                filename=f"test_v{version_num}.pdf",
                file_size=1024,
                storage_path=f"test/path/v{version_num}/test.pdf",
                change_description=f"Version {version_num}",
                change_type="update" if version_num > 1 else "create",
                created_by=agent.id,
            )
            await repo.create_from_create_schema(version_create)

        # Get all versions for document
        versions = await repo.get_by_document(doc.id)
        assert len(versions) == 3

        # Versions should be ordered by version_number ASC
        assert versions[0].version_number == 1
        assert versions[1].version_number == 2
        assert versions[2].version_number == 3

    @pytest.mark.asyncio
    async def test_get_by_document_and_version(self, db_manager):
        """Test getting specific version."""
        repo = VersionRepository(db_manager)

        # Create prerequisite entities
        org_repo = OrganizationRepository(db_manager)
        agent_repo = AgentRepository(db_manager)
        doc_repo = DocumentRepository(db_manager)

        # Create organization
        org_external_id = f"test-org-version-get-by-doc-ver-{uuid4()}"
        org_create = OrganizationCreate(
            name="Test Organization", external_id=org_external_id
        )
        org = await org_repo.create_from_create_schema(org_create)

        # Create agent
        agent_external_id = f"test-agent-version-get-by-doc-ver-{uuid4()}"
        agent_create = AgentCreate(
            organization_id=org.id, name="Test Agent", external_id=agent_external_id
        )
        agent = await agent_repo.create_from_create_schema(agent_create)

        # Create document
        doc_create = DocumentCreate(
            organization_id=org.id,
            name="Test Document for Version",
            filename="test.pdf",
            file_size=1024,
            storage_path="test/path/test.pdf",
            created_by=agent.id,
        )
        doc = await doc_repo.create_from_create_schema(doc_create)

        version_create = DocumentVersionCreate(
            document_id=doc.id,
            version_number=2,
            filename="test.pdf",
            file_size=1024,
            storage_path="test/path/v2/test.pdf",
            change_description="Version 2",
            change_type="update",
            created_by=agent.id,
        )
        version = await repo.create_from_create_schema(version_create)

        # Get specific version
        retrieved = await repo.get_by_document_and_version(doc.id, 2)
        assert retrieved is not None
        assert retrieved.id == version.id
        assert retrieved.version_number == 2

        # Try to get non-existent version
        not_found = await repo.get_by_document_and_version(doc.id, 99)
        assert not_found is None

    @pytest.mark.asyncio
    async def test_get_latest_version(self, db_manager):
        """Test getting the latest version for a document."""
        repo = VersionRepository(db_manager)

        # Create prerequisite entities
        org_repo = OrganizationRepository(db_manager)
        agent_repo = AgentRepository(db_manager)
        doc_repo = DocumentRepository(db_manager)

        # Create organization
        org_external_id = f"test-org-version-latest-{uuid4()}"
        org_create = OrganizationCreate(
            name="Test Organization", external_id=org_external_id
        )
        org = await org_repo.create_from_create_schema(org_create)

        # Create agent
        agent_external_id = f"test-agent-version-latest-{uuid4()}"
        agent_create = AgentCreate(
            organization_id=org.id, name="Test Agent", external_id=agent_external_id
        )
        agent = await agent_repo.create_from_create_schema(agent_create)

        # Create document
        doc_create = DocumentCreate(
            organization_id=org.id,
            name="Test Document for Latest Version",
            filename="test.pdf",
            file_size=1024,
            storage_path="test/path/test.pdf",
            created_by=agent.id,
        )
        doc = await doc_repo.create_from_create_schema(doc_create)

        # Create versions out of order
        for version_num in [1, 3, 2]:  # Not in order
            version_create = DocumentVersionCreate(
                document_id=doc.id,
                version_number=version_num,
                filename=f"test_v{version_num}.pdf",
                file_size=1024,
                storage_path=f"test/path/v{version_num}/test.pdf",
                change_description=f"Version {version_num}",
                change_type="update" if version_num > 1 else "create",
                created_by=agent.id,
            )
            await repo.create_from_create_schema(version_create)

        # Get latest version
        latest = await repo.get_latest_version(doc.id)
        assert latest is not None
        assert latest.version_number == 3  # Should be the highest number

    @pytest.mark.asyncio
    async def test_get_version_count(self, db_manager):
        """Test counting versions for a document."""
        repo = VersionRepository(db_manager)

        # Create prerequisite entities
        org_repo = OrganizationRepository(db_manager)
        agent_repo = AgentRepository(db_manager)
        doc_repo = DocumentRepository(db_manager)

        # Create organization
        org_external_id = f"test-org-version-count-{uuid4()}"
        org_create = OrganizationCreate(
            name="Test Organization", external_id=org_external_id
        )
        org = await org_repo.create_from_create_schema(org_create)

        # Create agent
        agent_external_id = f"test-agent-version-count-{uuid4()}"
        agent_create = AgentCreate(
            organization_id=org.id, name="Test Agent", external_id=agent_external_id
        )
        agent = await agent_repo.create_from_create_schema(agent_create)

        # Create document
        doc_create = DocumentCreate(
            organization_id=org.id,
            name="Test Document for Version Count",
            filename="test.pdf",
            file_size=1024,
            storage_path="test/path/test.pdf",
            created_by=agent.id,
        )
        doc = await doc_repo.create_from_create_schema(doc_create)

        # Create some versions
        for version_num in range(1, 4):
            version_create = DocumentVersionCreate(
                document_id=doc.id,
                version_number=version_num,
                filename=f"test_v{version_num}.pdf",
                file_size=1024,
                storage_path=f"test/path/v{version_num}/test.pdf",
                change_description=f"Version {version_num}",
                change_type="update" if version_num > 1 else "create",
                created_by=agent.id,
            )
            await repo.create_from_create_schema(version_create)

        # Count versions
        count = await repo.get_version_count(doc.id)
        assert count == 3

        # Count for non-existent document
        empty_count = await repo.get_version_count(uuid4())
        assert empty_count == 0

    @pytest.mark.asyncio
    async def test_create_initial_version(self, db_manager):
        """Test creating initial version for a document."""
        repo = VersionRepository(db_manager)

        # Create prerequisite entities
        org_repo = OrganizationRepository(db_manager)
        agent_repo = AgentRepository(db_manager)
        doc_repo = DocumentRepository(db_manager)

        # Create organization
        org_external_id = f"test-org-version-init-{uuid4()}"
        org_create = OrganizationCreate(
            name="Test Organization", external_id=org_external_id
        )
        org = await org_repo.create_from_create_schema(org_create)

        # Create agent
        agent_external_id = f"test-agent-version-init-{uuid4()}"
        agent_create = AgentCreate(
            organization_id=org.id, name="Test Agent", external_id=agent_external_id
        )
        agent = await agent_repo.create_from_create_schema(agent_create)

        # Create document
        doc_create = DocumentCreate(
            organization_id=org.id,
            name="Test Document for Initial Version",
            filename="test.pdf",
            file_size=1024,
            storage_path="test/path/test.pdf",
            created_by=agent.id,
        )
        doc = await doc_repo.create_from_create_schema(doc_create)

        # Create initial version
        version = await repo.create_initial_version(
            document_id=doc.id,
            filename="test.pdf",
            file_size=1024,
            storage_path="test/path/v1/test.pdf",
            mime_type="application/pdf",
            created_by=agent.id,
            metadata={"initial": True},
        )

        assert version.document_id == doc.id
        assert version.version_number == 1
        assert version.change_type == "create"
        assert version.change_description == "Initial version"
        assert version.metadata == {"initial": True}

    @pytest.mark.asyncio
    async def test_create_new_version(self, db_manager):
        """Test creating a new version for an existing document."""
        repo = VersionRepository(db_manager)

        # Create prerequisite entities
        org_repo = OrganizationRepository(db_manager)
        agent_repo = AgentRepository(db_manager)
        doc_repo = DocumentRepository(db_manager)

        # Create organization
        org_external_id = f"test-org-version-new-{uuid4()}"
        org_create = OrganizationCreate(
            name="Test Organization", external_id=org_external_id
        )
        org = await org_repo.create_from_create_schema(org_create)

        # Create agent
        agent_external_id = f"test-agent-version-new-{uuid4()}"
        agent_create = AgentCreate(
            organization_id=org.id, name="Test Agent", external_id=agent_external_id
        )
        agent = await agent_repo.create_from_create_schema(agent_create)

        # Create document
        doc_create = DocumentCreate(
            organization_id=org.id,
            name="Test Document for New Version",
            filename="test.pdf",
            file_size=1024,
            storage_path="test/path/test.pdf",
            created_by=agent.id,
        )
        doc = await doc_repo.create_from_create_schema(doc_create)

        # Create new version
        version = await repo.create_new_version(
            document_id=doc.id,
            version_number=2,
            filename="test_v2.pdf",
            file_size=2048,
            storage_path="test/path/v2/test.pdf",
            mime_type="application/pdf",
            created_by=agent.id,
            change_description="Updated content",
            change_type="update",
            metadata={"update": True},
        )

        assert version.document_id == doc.id
        assert version.version_number == 2
        assert version.change_type == "update"
        assert version.change_description == "Updated content"
        assert version.file_size == 2048
        assert version.metadata == {"update": True}

    @pytest.mark.asyncio
    async def test_update_version(self, db_manager):
        """Test updating version metadata."""
        repo = VersionRepository(db_manager)

        # Create prerequisite entities
        org_repo = OrganizationRepository(db_manager)
        agent_repo = AgentRepository(db_manager)
        doc_repo = DocumentRepository(db_manager)

        # Create organization
        org_external_id = f"test-org-version-update-{uuid4()}"
        org_create = OrganizationCreate(
            name="Test Organization", external_id=org_external_id
        )
        org = await org_repo.create_from_create_schema(org_create)

        # Create agent
        agent_external_id = f"test-agent-version-update-{uuid4()}"
        agent_create = AgentCreate(
            organization_id=org.id, name="Test Agent", external_id=agent_external_id
        )
        agent = await agent_repo.create_from_create_schema(agent_create)

        # Create document
        doc_create = DocumentCreate(
            organization_id=org.id,
            name="Test Document for Version Update",
            filename="test.pdf",
            file_size=1024,
            storage_path="test/path/test.pdf",
            created_by=agent.id,
        )
        doc = await doc_repo.create_from_create_schema(doc_create)

        version_create = DocumentVersionCreate(
            document_id=doc.id,
            version_number=1,
            filename="test.pdf",
            file_size=1024,
            storage_path="test/path/v1/test.pdf",
            change_description="Original description",
            change_type="create",
            created_by=agent.id,
        )
        version = await repo.create_from_create_schema(version_create)

        # Update version
        updates = {
            "change_description": "Updated description",
            "metadata": {"updated": True},
        }
        updated_version = await repo.update(version.id, updates)
        assert updated_version.change_description == "Updated description"
        assert updated_version.metadata == {"updated": True}

    @pytest.mark.asyncio
    async def test_delete_version(self, db_manager):
        """Test deleting versions."""
        repo = VersionRepository(db_manager)

        # Create prerequisite entities
        org_repo = OrganizationRepository(db_manager)
        agent_repo = AgentRepository(db_manager)
        doc_repo = DocumentRepository(db_manager)

        # Create organization
        org_external_id = f"test-org-version-delete-{uuid4()}"
        org_create = OrganizationCreate(
            name="Test Organization", external_id=org_external_id
        )
        org = await org_repo.create_from_create_schema(org_create)

        # Create agent
        agent_external_id = f"test-agent-version-delete-{uuid4()}"
        agent_create = AgentCreate(
            organization_id=org.id, name="Test Agent", external_id=agent_external_id
        )
        agent = await agent_repo.create_from_create_schema(agent_create)

        # Create document
        doc_create = DocumentCreate(
            organization_id=org.id,
            name="Test Document for Version Delete",
            filename="test.pdf",
            file_size=1024,
            storage_path="test/path/test.pdf",
            created_by=agent.id,
        )
        doc = await doc_repo.create_from_create_schema(doc_create)

        version_create = DocumentVersionCreate(
            document_id=doc.id,
            version_number=1,
            filename="test.pdf",
            file_size=1024,
            storage_path="test/path/v1/test.pdf",
            change_description="Test version",
            change_type="create",
            created_by=agent.id,
        )
        version = await repo.create_from_create_schema(version_create)

        # Delete version
        deleted = await repo.delete(version.id)
        assert deleted

        # Verify it's gone
        retrieved = await repo.get_by_id(version.id)
        assert retrieved is None
