"""
Tests for Document repository.

This module tests the DocumentRepository class methods.
"""

import pytest
from uuid import uuid4

from doc_vault.database.repositories.document import DocumentRepository
from doc_vault.database.repositories.organization import OrganizationRepository
from doc_vault.database.repositories.agent import AgentRepository
from doc_vault.database.schemas.document import DocumentCreate
from doc_vault.database.schemas.organization import OrganizationCreate
from doc_vault.database.schemas.agent import AgentCreate


class TestDocumentRepository:
    """Test Document repository operations."""

    @pytest.mark.asyncio
    async def test_create_and_get_document(self, db_manager):
        """Test creating and retrieving documents."""
        # Create prerequisite repositories
        org_repo = OrganizationRepository(db_manager)
        agent_repo = AgentRepository(db_manager)
        doc_repo = DocumentRepository(db_manager)

        # Create organization
        org_external_id = f"test-org-doc-{uuid4()}"
        org_create = OrganizationCreate(
            external_id=org_external_id,
            name="Test Organization for Document",
        )
        org = await org_repo.create_from_create_schema(org_create)

        # Create agent
        agent_external_id = f"test-agent-doc-{uuid4()}"
        agent_create = AgentCreate(
            external_id=agent_external_id,
            organization_id=str(org.id),
            name="Test Agent for Document",
        )
        agent = await agent_repo.create_from_create_schema(agent_create)

        doc_create = DocumentCreate(
            organization_id=org.id,
            name="Test Document",
            filename="test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            storage_path="test/path/test.pdf",
            created_by=agent.id,
            description="Test document",
            tags=["test"],
            metadata={"test": True},
        )

        # Create document
        doc = await doc_repo.create_from_create_schema(doc_create)
        assert doc.organization_id == org.id
        assert doc.name == "Test Document"
        assert doc.filename == "test.pdf"
        assert doc.current_version == 1

        # Get by ID
        retrieved = await doc_repo.get_by_id(doc.id)
        assert retrieved.id == doc.id
        assert retrieved.name == "Test Document"

    @pytest.mark.asyncio
    async def test_get_by_organization(self, db_manager):
        """Test getting documents by organization."""
        # Create prerequisite repositories
        org_repo = OrganizationRepository(db_manager)
        agent_repo = AgentRepository(db_manager)
        doc_repo = DocumentRepository(db_manager)

        # Create organization
        org_external_id = f"test-org-doc-get-by-org-{uuid4()}"
        org_create = OrganizationCreate(
            external_id=org_external_id,
            name="Test Organization for Get By Organization",
        )
        org = await org_repo.create_from_create_schema(org_create)

        # Create agent
        agent_external_id = f"test-agent-doc-get-by-org-{uuid4()}"
        agent_create = AgentCreate(
            external_id=agent_external_id,
            organization_id=str(org.id),
            name="Test Agent for Get By Organization",
        )
        agent = await agent_repo.create_from_create_schema(agent_create)

        # Create multiple documents
        for i in range(3):
            doc_create = DocumentCreate(
                organization_id=org.id,
                name=f"Test Document {i}",
                filename=f"test{i}.pdf",
                file_size=1024,
                storage_path=f"test/path/test{i}.pdf",
                created_by=agent.id,
                description=f"Test document {i}",
                tags=["test"],
                metadata={"test": True, "index": i},
            )
            await doc_repo.create_from_create_schema(doc_create)

        # Get by organization
        docs = await doc_repo.get_by_organization(org.id)
        assert len(docs) == 3
        assert all(doc.organization_id == org.id for doc in docs)

    @pytest.mark.asyncio
    async def test_update_document(self, db_manager):
        """Test updating document fields."""
        # Create prerequisite repositories
        org_repo = OrganizationRepository(db_manager)
        agent_repo = AgentRepository(db_manager)
        doc_repo = DocumentRepository(db_manager)

        # Create organization
        org_external_id = f"test-org-doc-update-{uuid4()}"
        org_create = OrganizationCreate(
            external_id=org_external_id,
            name="Test Organization for Document Update",
        )
        org = await org_repo.create_from_create_schema(org_create)

        # Create agent
        agent_external_id = f"test-agent-doc-update-{uuid4()}"
        agent_create = AgentCreate(
            external_id=agent_external_id,
            organization_id=str(org.id),
            name="Test Agent for Document Update",
        )
        agent = await agent_repo.create_from_create_schema(agent_create)

        doc_create = DocumentCreate(
            organization_id=org.id,
            name="Original Name",
            filename="test.pdf",
            file_size=1024,
            storage_path="test/path/test.pdf",
            created_by=agent.id,
            description="Original description",
            tags=["test"],
            metadata={"test": True},
        )
        doc = await doc_repo.create_from_create_schema(doc_create)

        # Update document
        updates = {
            "name": "Updated Name",
            "description": "Updated description",
            "current_version": 2,
        }
        updated_doc = await doc_repo.update(doc.id, updates)
        assert updated_doc.name == "Updated Name"
        assert updated_doc.description == "Updated description"
        assert updated_doc.current_version == 2

    @pytest.mark.asyncio
    async def test_search_documents(self, db_manager):
        """Test document search functionality."""
        repo = DocumentRepository(db_manager)

        # Create prerequisite entities
        org_repo = OrganizationRepository(db_manager)
        agent_repo = AgentRepository(db_manager)

        # Create organization
        org_external_id = f"test-org-search-{uuid4()}"
        org_create = OrganizationCreate(
            name="Test Organization", external_id=org_external_id
        )
        org = await org_repo.create_from_create_schema(org_create)
        org_id = org.id

        # Create agent
        agent_external_id = f"test-agent-search-{uuid4()}"
        agent_create = AgentCreate(
            organization_id=org_id, name="Test Agent", external_id=agent_external_id
        )
        agent = await agent_repo.create_from_create_schema(agent_create)
        agent_id = agent.id

        # Create documents with searchable content
        docs_data = [
            ("Annual Report 2024", "This is the annual report for 2024"),
            ("Quarterly Review Q1", "Q1 quarterly review document"),
            ("Budget Planning", "Annual budget planning document"),
        ]

        created_docs = []
        for name, desc in docs_data:
            doc_create = DocumentCreate(
                organization_id=org_id,
                name=name,
                description=desc,
                filename="test.pdf",
                file_size=1024,
                storage_path="test/path/test.pdf",
                created_by=agent_id,
            )
            doc = await repo.create_from_create_schema(doc_create)
            created_docs.append(doc)

        # Search for "annual"
        results = await repo.search_by_name(org_id, "annual", limit=10)
        assert len(results) == 1  # Should find only the document with "Annual" in name

        # Search for "quarterly"
        results = await repo.search_by_name(org_id, "quarterly", limit=10)
        assert len(results) >= 1

        # Search for non-existent term
        results = await repo.search_by_name(org_id, "nonexistent", limit=10)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_list_documents_with_filters(self, db_manager):
        """Test listing documents with various filters."""
        repo = DocumentRepository(db_manager)

        # Create prerequisite entities
        org_repo = OrganizationRepository(db_manager)
        agent_repo = AgentRepository(db_manager)

        # Create organization
        org_external_id = f"test-org-filters-{uuid4()}"
        org_create = OrganizationCreate(
            name="Test Organization", external_id=org_external_id
        )
        org = await org_repo.create_from_create_schema(org_create)
        org_id = org.id

        # Create agent
        agent_external_id = f"test-agent-filters-{uuid4()}"
        agent_create = AgentCreate(
            organization_id=org_id, name="Test Agent", external_id=agent_external_id
        )
        agent = await agent_repo.create_from_create_schema(agent_create)
        agent_id = agent.id

        # Create documents with different statuses and tags
        statuses = ["active", "draft", "archived"]
        tags_list = [["finance"], ["hr", "policy"], ["legal"]]

        for i, (status, tags) in enumerate(zip(statuses, tags_list)):
            doc_create = DocumentCreate(
                organization_id=org_id,
                name=f"Document {i}",
                filename=f"test{i}.pdf",
                file_size=1024,
                storage_path=f"test/path/test{i}.pdf",
                created_by=agent_id,
                tags=tags,
            )
            doc = await repo.create_from_create_schema(doc_create)

            # Update status if not active
            if status != "active":
                await repo.update(doc.id, {"status": status})

        # List all documents
        docs = await repo.get_by_organization(org_id)
        assert len(docs) == 3

        # Filter by status
        active_docs = await repo.get_by_organization(org_id, status="active")
        assert len(active_docs) == 1

        draft_docs = await repo.get_by_organization(org_id, status="draft")
        assert len(draft_docs) == 1

        # Filter by tags (only active documents)
        finance_docs = await repo.get_by_tags(org_id, ["finance"])
        assert len(finance_docs) == 1

        # Note: hr_docs test removed since document with "hr" tag has status "draft"
        # and get_by_tags only returns active documents

    @pytest.mark.asyncio
    async def test_delete_document(self, db_manager):
        """Test soft deleting documents."""
        # Create prerequisite repositories
        org_repo = OrganizationRepository(db_manager)
        agent_repo = AgentRepository(db_manager)
        doc_repo = DocumentRepository(db_manager)

        # Create organization
        org_external_id = f"test-org-doc-delete-{uuid4()}"
        org_create = OrganizationCreate(
            external_id=org_external_id,
            name="Test Organization for Document Delete",
        )
        org = await org_repo.create_from_create_schema(org_create)

        # Create agent
        agent_external_id = f"test-agent-doc-delete-{uuid4()}"
        agent_create = AgentCreate(
            external_id=agent_external_id,
            organization_id=str(org.id),
            name="Test Agent for Document Delete",
        )
        agent = await agent_repo.create_from_create_schema(agent_create)

        doc_create = DocumentCreate(
            organization_id=org.id,
            name="Test Document",
            filename="test.pdf",
            file_size=1024,
            storage_path="test/path/test.pdf",
            created_by=agent.id,
            description="Test document for deletion",
            tags=["test"],
            metadata={"test": True},
        )
        doc = await doc_repo.create_from_create_schema(doc_create)

        # Soft delete
        deleted = await doc_repo.delete(doc.id)
        assert deleted

        # Document should still exist but be marked as deleted
        retrieved = await doc_repo.get_by_id(doc.id)
        assert retrieved.status == "deleted"

        # Should not appear in normal listings
        docs = await doc_repo.get_by_organization(org.id, status="active")
        assert not any(d.id == doc.id for d in docs)

    @pytest.mark.asyncio
    async def test_get_by_creator(self, db_manager):
        """Test getting documents by creator."""
        repo = DocumentRepository(db_manager)

        # Create prerequisite entities
        org_repo = OrganizationRepository(db_manager)
        agent_repo = AgentRepository(db_manager)

        # Create organization
        org_external_id = f"test-org-creator-{uuid4()}"
        org_create = OrganizationCreate(
            name="Test Organization", external_id=org_external_id
        )
        org = await org_repo.create_from_create_schema(org_create)
        org_id = org.id

        # Create two agents
        agent1_external_id = f"test-agent-creator-1-{uuid4()}"
        agent1_create = AgentCreate(
            organization_id=org_id,
            name="Test Agent 1",
            external_id=agent1_external_id,
        )
        agent1 = await agent_repo.create_from_create_schema(agent1_create)
        agent1_id = agent1.id

        agent2_external_id = f"test-agent-creator-2-{uuid4()}"
        agent2_create = AgentCreate(
            organization_id=org_id,
            name="Test Agent 2",
            external_id=agent2_external_id,
        )
        agent2 = await agent_repo.create_from_create_schema(agent2_create)
        agent2_id = agent2.id

        # Create documents by different agents
        for agent_id in [agent1_id, agent2_id]:
            for i in range(2):
                doc_create = DocumentCreate(
                    organization_id=org_id,
                    name=f"Document by agent {agent_id} - {i}",
                    filename=f"test{i}.pdf",
                    file_size=1024,
                    storage_path=f"test/path/test{i}.pdf",
                    created_by=agent_id,
                )
                await repo.create_from_create_schema(doc_create)

        # Get documents by agent1
        agent1_docs = await repo.get_by_created_by(agent1_id)
        assert len(agent1_docs) == 2
        assert all(doc.created_by == agent1_id for doc in agent1_docs)

        # Get documents by agent2
        agent2_docs = await repo.get_by_created_by(agent2_id)
        assert len(agent2_docs) == 2
        assert all(doc.created_by == agent2_id for doc in agent2_docs)
