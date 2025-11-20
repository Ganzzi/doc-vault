"""
Tests for ACL Repository (v2.0).

Tests cover:
- ACL creation with UUID-based operations
- Permission management (READ, WRITE, DELETE, SHARE, ADMIN)
- get_all_permissions() method
- set_permissions() bulk operation method
- check_permission() and get_by_agent()
- Expiration and metadata handling
"""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta, timezone

from doc_vault.database.repositories.acl import ACLRepository
from doc_vault.database.repositories.document import DocumentRepository
from doc_vault.database.repositories.organization import OrganizationRepository
from doc_vault.database.repositories.agent import AgentRepository
from doc_vault.database.schemas.acl import DocumentACL, DocumentACLCreate
from doc_vault.database.schemas.document import DocumentCreate
from doc_vault.database.schemas.organization import OrganizationCreate
from doc_vault.database.schemas.agent import AgentCreate


@pytest.fixture
async def acl_repo(db_manager):
    """Create an ACL repository."""
    return ACLRepository(db_manager)


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
async def agent1(agent_repo, organization):
    """Create first test agent."""
    agent_id = uuid4()
    create_data = AgentCreate(id=agent_id, organization_id=organization.id)
    return await agent_repo.create(create_data)


@pytest.fixture
async def agent2(agent_repo, organization):
    """Create second test agent."""
    agent_id = uuid4()
    create_data = AgentCreate(id=agent_id, organization_id=organization.id)
    return await agent_repo.create(create_data)


@pytest.fixture
async def document(doc_repo, organization, agent1):
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
        created_by=agent1.id,
        updated_by=agent1.id,
    )
    return await doc_repo.create(create_data)


class TestACLCreate:
    """Test ACL creation and permission granting."""

    async def test_grant_read_permission(self, acl_repo, document, agent1, agent2):
        """Test granting READ permission."""
        acl_id = uuid4()
        create_data = DocumentACLCreate(
            id=acl_id,
            document_id=document.id,
            agent_id=agent2.id,
            permission="READ",
            granted_by=agent1.id,
        )

        acl = await acl_repo.create(create_data)

        assert acl.id == acl_id
        assert acl.document_id == document.id
        assert acl.agent_id == agent2.id
        assert acl.permission == "READ"
        assert acl.granted_by == agent1.id

    async def test_grant_multiple_permissions(self, acl_repo, document, agent1, agent2):
        """Test granting different permissions."""
        permissions = ["READ", "WRITE", "DELETE", "SHARE", "ADMIN"]

        for perm in permissions:
            acl_id = uuid4()
            create_data = DocumentACLCreate(
                id=acl_id,
                document_id=document.id,
                agent_id=agent2.id,
                permission=perm,
                granted_by=agent1.id,
            )
            acl = await acl_repo.create(create_data)
            assert acl.permission == perm

    async def test_grant_permission_with_expiration(
        self, acl_repo, document, agent1, agent2
    ):
        """Test granting permission with expiration date."""
        acl_id = uuid4()
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        create_data = DocumentACLCreate(
            id=acl_id,
            document_id=document.id,
            agent_id=agent2.id,
            permission="READ",
            granted_by=agent1.id,
            expires_at=expires_at,
        )

        acl = await acl_repo.create(create_data)

        assert acl.expires_at is not None

    async def test_grant_permission_with_metadata(
        self, acl_repo, document, agent1, agent2
    ):
        """Test granting permission with metadata."""
        acl_id = uuid4()
        metadata = {"reason": "temporary_access", "requestor": "manager"}

        create_data = DocumentACLCreate(
            id=acl_id,
            document_id=document.id,
            agent_id=agent2.id,
            permission="READ",
            granted_by=agent1.id,
            metadata=metadata,
        )

        acl = await acl_repo.create(create_data)

        assert acl.metadata == metadata


class TestACLGet:
    """Test ACL retrieval operations."""

    async def test_get_by_id(self, acl_repo, document, agent1, agent2):
        """Test getting ACL by ID."""
        acl_id = uuid4()
        create_data = DocumentACLCreate(
            id=acl_id,
            document_id=document.id,
            agent_id=agent2.id,
            permission="READ",
            granted_by=agent1.id,
        )
        await acl_repo.create(create_data)

        acl = await acl_repo.get_by_id(acl_id)

        assert acl is not None
        assert acl.id == acl_id
        assert acl.permission == "READ"

    async def test_get_by_document(self, acl_repo, document, agent1, agent2):
        """Test getting all ACLs for a document."""
        # Grant multiple permissions
        for perm in ["READ", "WRITE", "DELETE"]:
            acl_id = uuid4()
            create_data = DocumentACLCreate(
                id=acl_id,
                document_id=document.id,
                agent_id=agent2.id,
                permission=perm,
                granted_by=agent1.id,
            )
            await acl_repo.create(create_data)

        # Get all permissions
        acls = await acl_repo.get_by_document(document.id)

        assert len(acls) >= 3

    async def test_get_by_agent(self, acl_repo, document, agent1, agent2):
        """Test getting all ACLs for an agent."""
        # Grant agent multiple document permissions
        for i in range(3):
            doc_id = uuid4()
            from doc_vault.database.schemas.document import DocumentCreate

            doc_create = DocumentCreate(
                id=doc_id,
                organization_id=document.organization_id,
                name=f"Doc{i}.pdf",
                filename=f"doc{i}.pdf",
                file_size=1024,
                mime_type="application/pdf",
                storage_path=f"docs/{doc_id}/doc{i}.pdf",
                created_by=agent1.id,
                updated_by=agent1.id,
            )
            from doc_vault.database.repositories.document import DocumentRepository

            doc_repo = DocumentRepository(acl_repo.db_manager)
            created_doc = await doc_repo.create(doc_create)

            acl_id = uuid4()
            acl_create = DocumentACLCreate(
                id=acl_id,
                document_id=created_doc.id,
                agent_id=agent2.id,
                permission="READ",
                granted_by=agent1.id,
            )
            await acl_repo.create(acl_create)

        # Get all ACLs for agent2
        acls = await acl_repo.get_by_agent(agent2.id)

        assert len(acls) >= 3


class TestACLCheckPermission:
    """Test permission checking."""

    async def test_check_permission_granted(self, acl_repo, document, agent1, agent2):
        """Test checking permission that was granted."""
        acl_id = uuid4()
        create_data = DocumentACLCreate(
            id=acl_id,
            document_id=document.id,
            agent_id=agent2.id,
            permission="READ",
            granted_by=agent1.id,
        )
        await acl_repo.create(create_data)

        # Check permission
        has_permission = await acl_repo.check_permission(document.id, agent2.id, "READ")

        assert has_permission is True

    async def test_check_permission_not_granted(
        self, acl_repo, document, agent1, agent2
    ):
        """Test checking permission that was not granted."""
        acl_id = uuid4()
        create_data = DocumentACLCreate(
            id=acl_id,
            document_id=document.id,
            agent_id=agent2.id,
            permission="READ",
            granted_by=agent1.id,
        )
        await acl_repo.create(create_data)

        # Check different permission
        has_permission = await acl_repo.check_permission(
            document.id, agent2.id, "WRITE"
        )

        assert has_permission is False

    async def test_check_admin_inherits_all(self, acl_repo, document, agent1, agent2):
        """Test that ADMIN permission implies all others."""
        acl_id = uuid4()
        create_data = DocumentACLCreate(
            id=acl_id,
            document_id=document.id,
            agent_id=agent2.id,
            permission="ADMIN",
            granted_by=agent1.id,
        )
        await acl_repo.create(create_data)

        # Check all permissions (ADMIN should include all)
        permissions = ["READ", "WRITE", "DELETE", "SHARE", "ADMIN"]
        for perm in permissions:
            has_permission = await acl_repo.check_permission(
                document.id, agent2.id, perm
            )
            assert has_permission is True


class TestACLDelete:
    """Test ACL deletion and revocation."""

    async def test_delete_permission(self, acl_repo, document, agent1, agent2):
        """Test deleting a permission."""
        acl_id = uuid4()
        create_data = DocumentACLCreate(
            id=acl_id,
            document_id=document.id,
            agent_id=agent2.id,
            permission="READ",
            granted_by=agent1.id,
        )
        await acl_repo.create(create_data)

        # Delete permission
        result = await acl_repo.delete(acl_id)

        assert result is True

        # Permission should be gone
        has_permission = await acl_repo.check_permission(document.id, agent2.id, "READ")
        assert has_permission is False


class TestACLBulkOperations:
    """Test bulk permission operations."""

    async def test_get_all_permissions(self, acl_repo, document, agent1, agent2):
        """Test getting all permissions for a document."""
        # Grant multiple permissions
        permissions_to_grant = [
            ("READ", agent1.id),
            ("WRITE", agent2.id),
            ("DELETE", agent1.id),
        ]

        for perm, agent_id in permissions_to_grant:
            acl_id = uuid4()
            create_data = DocumentACLCreate(
                id=acl_id,
                document_id=document.id,
                agent_id=agent_id,
                permission=perm,
                granted_by=agent1.id,
            )
            await acl_repo.create(create_data)

        # Get all permissions
        all_perms = await acl_repo.get_all_permissions(document.id)

        assert len(all_perms) >= 3

    async def test_set_permissions_bulk(self, acl_repo, document, agent1, agent2):
        """Test bulk setting permissions (replace all)."""
        # New permissions to set
        new_permissions = [
            {"agent_id": agent1.id, "permission": "ADMIN"},
            {"agent_id": agent2.id, "permission": "READ"},
        ]

        # Set permissions (should replace existing)
        await acl_repo.set_permissions(document.id, new_permissions, agent1.id)

        # Verify new permissions
        acls = await acl_repo.get_by_document(document.id)

        # Should have exactly the new permissions (or at least include them)
        assert len(acls) >= len(new_permissions)

