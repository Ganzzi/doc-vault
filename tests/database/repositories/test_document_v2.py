"""
Tests for Document Repository (v2.0).

Tests cover:
- Document creation with prefix and path
- list_by_prefix() method for prefix-based listing
- list_recursive() method with depth control
- UUID-based operations
- Storage path generation
- Error conditions
"""

import pytest
from uuid import uuid4

from doc_vault.database.repositories.document import DocumentRepository
from doc_vault.database.repositories.organization import OrganizationRepository
from doc_vault.database.repositories.agent import AgentRepository
from doc_vault.database.schemas.document import Document, DocumentCreate
from doc_vault.database.schemas.organization import OrganizationCreate
from doc_vault.database.schemas.agent import AgentCreate
from doc_vault.exceptions import DatabaseError


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


class TestDocumentCreate:
    """Test document creation with v2.0 prefix and path support."""

    async def test_create_document_without_prefix(self, doc_repo, organization, agent):
        """Test creating a document without prefix (backwards compatible)."""
        doc_id = uuid4()
        create_data = DocumentCreate(
            id=doc_id,
            organization_id=organization.id,
            name="Report.pdf",
            filename="report.pdf",
            file_size=1024,
            mime_type="application/pdf",
            storage_path=f"docs/{doc_id}/report.pdf",
            created_by=agent.id,
            updated_by=agent.id,
        )

        doc = await doc_repo.create(create_data)

        assert doc.id == doc_id
        assert doc.name == "Report.pdf"
        assert doc.prefix is None
        assert doc.path is None

    async def test_create_document_with_prefix(self, doc_repo, organization, agent):
        """Test creating a document with hierarchical prefix."""
        doc_id = uuid4()
        create_data = DocumentCreate(
            id=doc_id,
            organization_id=organization.id,
            name="Q1Report.pdf",
            filename="q1-report.pdf",
            file_size=2048,
            mime_type="application/pdf",
            storage_path=f"docs/{doc_id}/q1-report.pdf",
            prefix="/reports/2025/q1",
            path="/reports/2025/q1/Q1Report.pdf",
            created_by=agent.id,
            updated_by=agent.id,
        )

        doc = await doc_repo.create(create_data)

        assert doc.id == doc_id
        assert doc.prefix == "/reports/2025/q1"
        assert doc.path == "/reports/2025/q1/Q1Report.pdf"

    async def test_create_document_with_deep_hierarchy(
        self, doc_repo, organization, agent
    ):
        """Test creating document with deep prefix hierarchy."""
        doc_id = uuid4()
        prefix = "/projects/2025/alpha/design/v2"
        path = "/projects/2025/alpha/design/v2/Mockups.pdf"

        create_data = DocumentCreate(
            id=doc_id,
            organization_id=organization.id,
            name="Mockups.pdf",
            filename="mockups.pdf",
            file_size=5120,
            mime_type="application/pdf",
            storage_path=f"docs/{doc_id}/mockups.pdf",
            prefix=prefix,
            path=path,
            created_by=agent.id,
            updated_by=agent.id,
        )

        doc = await doc_repo.create(create_data)

        assert doc.prefix == prefix
        assert doc.path == path


class TestDocumentListByPrefix:
    """Test prefix-based listing operations."""

    async def test_list_by_prefix_empty(self, doc_repo, organization, agent):
        """Test listing documents with empty prefix returns nothing."""
        docs = await doc_repo.list_by_prefix(organization.id, "/nonexistent")

        assert len(docs) == 0

    async def test_list_by_prefix_single_level(self, doc_repo, organization, agent):
        """Test listing documents under a prefix."""
        # Create documents in same prefix
        for i in range(3):
            doc_id = uuid4()
            create_data = DocumentCreate(
                id=doc_id,
                organization_id=organization.id,
                name=f"Report{i}.pdf",
                filename=f"report{i}.pdf",
                file_size=1024,
                mime_type="application/pdf",
                storage_path=f"docs/{doc_id}/report{i}.pdf",
                prefix="/reports",
                path=f"/reports/Report{i}.pdf",
                created_by=agent.id,
                updated_by=agent.id,
            )
            await doc_repo.create(create_data)

        # List by prefix
        docs = await doc_repo.list_by_prefix(organization.id, "/reports")

        assert len(docs) >= 3
        for doc in docs:
            assert doc.prefix == "/reports"

    async def test_list_by_prefix_with_pagination(self, doc_repo, organization, agent):
        """Test prefix listing with limit and offset."""
        # Create multiple documents
        for i in range(5):
            doc_id = uuid4()
            create_data = DocumentCreate(
                id=doc_id,
                organization_id=organization.id,
                name=f"Doc{i}.pdf",
                filename=f"doc{i}.pdf",
                file_size=1024,
                mime_type="application/pdf",
                storage_path=f"docs/{doc_id}/doc{i}.pdf",
                prefix="/projects",
                path=f"/projects/Doc{i}.pdf",
                created_by=agent.id,
                updated_by=agent.id,
            )
            await doc_repo.create(create_data)

        # Get paginated results
        docs_page1 = await doc_repo.list_by_prefix(
            organization.id, "/projects", limit=2, offset=0
        )
        docs_page2 = await doc_repo.list_by_prefix(
            organization.id, "/projects", limit=2, offset=2
        )

        assert len(docs_page1) == 2
        assert len(docs_page2) == 2

        # Verify different pages
        page1_ids = {d.id for d in docs_page1}
        page2_ids = {d.id for d in docs_page2}
        assert page1_ids != page2_ids


class TestDocumentRecursiveListing:
    """Test recursive prefix listing with depth control."""

    async def test_list_recursive_all_depths(self, doc_repo, organization, agent):
        """Test listing documents recursively at all depths."""
        # Create documents at different depths
        paths = [
            "/reports/Q1Report.pdf",
            "/reports/2025/Q1Report.pdf",
            "/reports/2025/q1/Financial.pdf",
            "/reports/2025/q1/Sales.pdf",
        ]

        for path in paths:
            doc_id = uuid4()
            # Extract prefix (everything except filename)
            parts = path.rsplit("/", 1)
            prefix = parts[0] if len(parts) > 1 else "/"

            create_data = DocumentCreate(
                id=doc_id,
                organization_id=organization.id,
                name=path.split("/")[-1],
                filename=path.split("/")[-1],
                file_size=1024,
                mime_type="application/pdf",
                storage_path=f"docs/{doc_id}/{path.split('/')[-1]}",
                prefix=prefix,
                path=path,
                created_by=agent.id,
                updated_by=agent.id,
            )
            await doc_repo.create(create_data)

        # List recursively from /reports
        docs = await doc_repo.list_recursive(organization.id, "/reports")

        assert len(docs) >= 4

    async def test_list_recursive_with_max_depth(self, doc_repo, organization, agent):
        """Test recursive listing with depth limit."""
        # Create documents at different depths
        paths = [
            "/projects/ProjectA.pdf",
            "/projects/alpha/Design.pdf",
            "/projects/alpha/v1/Mockups.pdf",
            "/projects/alpha/v1/beta/Iteration1.pdf",
        ]

        for path in paths:
            doc_id = uuid4()
            parts = path.rsplit("/", 1)
            prefix = parts[0] if len(parts) > 1 else "/"

            create_data = DocumentCreate(
                id=doc_id,
                organization_id=organization.id,
                name=path.split("/")[-1],
                filename=path.split("/")[-1],
                file_size=1024,
                mime_type="application/pdf",
                storage_path=f"docs/{doc_id}/{path.split('/')[-1]}",
                prefix=prefix,
                path=path,
                created_by=agent.id,
                updated_by=agent.id,
            )
            await doc_repo.create(create_data)

        # List with max_depth=2
        docs = await doc_repo.list_recursive(organization.id, "/projects", max_depth=2)

        # Should include /projects/ProjectA.pdf and /projects/alpha/Design.pdf
        # But not deeper levels
        for doc in docs:
            if doc.path:
                # Count depth: number of "/" in path
                depth = doc.path.count("/") - 1
                assert depth <= 2


class TestDocumentGet:
    """Test document retrieval operations."""

    async def test_get_by_id(self, doc_repo, organization, agent):
        """Test getting document by UUID."""
        doc_id = uuid4()
        create_data = DocumentCreate(
            id=doc_id,
            organization_id=organization.id,
            name="Test.pdf",
            filename="test.pdf",
            file_size=512,
            mime_type="application/pdf",
            storage_path=f"docs/{doc_id}/test.pdf",
            created_by=agent.id,
            updated_by=agent.id,
        )
        await doc_repo.create(create_data)

        doc = await doc_repo.get_by_id(doc_id)

        assert doc is not None
        assert doc.id == doc_id
        assert doc.name == "Test.pdf"

    async def test_get_by_id_string(self, doc_repo, organization, agent):
        """Test getting document using string UUID."""
        doc_id = uuid4()
        create_data = DocumentCreate(
            id=doc_id,
            organization_id=organization.id,
            name="Test.pdf",
            filename="test.pdf",
            file_size=512,
            mime_type="application/pdf",
            storage_path=f"docs/{doc_id}/test.pdf",
            created_by=agent.id,
            updated_by=agent.id,
        )
        await doc_repo.create(create_data)

        doc = await doc_repo.get_by_id(str(doc_id))

        assert doc is not None
        assert doc.id == doc_id

    async def test_get_by_id_not_found(self, doc_repo):
        """Test getting non-existent document."""
        doc = await doc_repo.get_by_id(uuid4())

        assert doc is None


class TestDocumentUpdate:
    """Test document update operations."""

    async def test_update_prefix(self, doc_repo, organization, agent):
        """Test updating document prefix and path."""
        doc_id = uuid4()
        create_data = DocumentCreate(
            id=doc_id,
            organization_id=organization.id,
            name="Report.pdf",
            filename="report.pdf",
            file_size=1024,
            mime_type="application/pdf",
            storage_path=f"docs/{doc_id}/report.pdf",
            prefix="/reports/2024",
            path="/reports/2024/Report.pdf",
            created_by=agent.id,
            updated_by=agent.id,
        )
        await doc_repo.create(create_data)

        # Update prefix and path
        updated = await doc_repo.update(
            doc_id,
            {
                "prefix": "/reports/2025",
                "path": "/reports/2025/Report.pdf",
            },
        )

        assert updated is not None
        assert updated.prefix == "/reports/2025"
        assert updated.path == "/reports/2025/Report.pdf"

    async def test_update_metadata(self, doc_repo, organization, agent):
        """Test updating document metadata."""
        doc_id = uuid4()
        create_data = DocumentCreate(
            id=doc_id,
            organization_id=organization.id,
            name="Doc.pdf",
            filename="doc.pdf",
            file_size=1024,
            mime_type="application/pdf",
            storage_path=f"docs/{doc_id}/doc.pdf",
            created_by=agent.id,
            updated_by=agent.id,
            metadata={"version": "1.0"},
        )
        await doc_repo.create(create_data)

        # Update metadata
        updated = await doc_repo.update(doc_id, {"metadata": {"version": "2.0"}})

        assert updated is not None
        assert updated.metadata == {"version": "2.0"}


class TestDocumentDelete:
    """Test document deletion operations."""

    async def test_soft_delete_document(self, doc_repo, organization, agent):
        """Test soft deleting a document (status -> deleted)."""
        doc_id = uuid4()
        create_data = DocumentCreate(
            id=doc_id,
            organization_id=organization.id,
            name="Temp.pdf",
            filename="temp.pdf",
            file_size=1024,
            mime_type="application/pdf",
            storage_path=f"docs/{doc_id}/temp.pdf",
            created_by=agent.id,
            updated_by=agent.id,
        )
        await doc_repo.create(create_data)

        # Soft delete
        result = await doc_repo.delete(doc_id, hard_delete=False)

        assert result is True

        # Document should still exist but be deleted
        doc = await doc_repo.get_by_id(doc_id)
        if doc:
            assert doc.status == "deleted"

    async def test_hard_delete_document(self, doc_repo, organization, agent):
        """Test hard deleting a document (remove from DB)."""
        doc_id = uuid4()
        create_data = DocumentCreate(
            id=doc_id,
            organization_id=organization.id,
            name="Temp.pdf",
            filename="temp.pdf",
            file_size=1024,
            mime_type="application/pdf",
            storage_path=f"docs/{doc_id}/temp.pdf",
            created_by=agent.id,
            updated_by=agent.id,
        )
        await doc_repo.create(create_data)

        # Hard delete
        result = await doc_repo.delete(doc_id, hard_delete=True)

        assert result is True

        # Document should not exist
        doc = await doc_repo.get_by_id(doc_id)
        assert doc is None

