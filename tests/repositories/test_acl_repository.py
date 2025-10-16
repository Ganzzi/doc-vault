"""
Tests for ACL repository.

This module tests the ACLRepository class methods.
"""

import pytest
from uuid import uuid4

from doc_vault.database.repositories.acl import ACLRepository
from doc_vault.database.repositories.agent import AgentRepository
from doc_vault.database.repositories.document import DocumentRepository
from doc_vault.database.repositories.organization import OrganizationRepository
from doc_vault.database.schemas.acl import DocumentACLCreate
from doc_vault.database.schemas.agent import AgentCreate
from doc_vault.database.schemas.document import DocumentCreate
from doc_vault.database.schemas.organization import OrganizationCreate


class TestACLRepository:
    """Test ACL repository operations."""

    @pytest.mark.asyncio
    async def test_create_and_get_acl(self, db_manager):
        """Test creating and retrieving ACL entries."""
        # Create required entities first
        org_repo = OrganizationRepository(db_manager)
        agent_repo = AgentRepository(db_manager)
        doc_repo = DocumentRepository(db_manager)
        acl_repo = ACLRepository(db_manager)

        # Create organization
        org_external_id = f"test-org-acl-{uuid4()}"
        org_create = OrganizationCreate(
            external_id=org_external_id,
            name="Test Organization for ACL",
        )
        org = await org_repo.create_from_create_schema(org_create)

        # Create agents
        agent_external_id = f"test-agent-acl-{uuid4()}"
        agent_create = AgentCreate(
            external_id=agent_external_id,
            organization_id=str(org.id),
            name="Test Agent for ACL",
        )
        agent = await agent_repo.create_from_create_schema(agent_create)

        granter_external_id = f"test-granter-acl-{uuid4()}"
        granted_by_create = AgentCreate(
            external_id=granter_external_id,
            organization_id=str(org.id),
            name="Test Granter for ACL",
        )
        granter = await agent_repo.create_from_create_schema(granted_by_create)

        # Create document
        doc_create = DocumentCreate(
            organization_id=org.id,
            name="Test Document for ACL",
            filename="test.pdf",
            file_size=1024,
            storage_path="test/path/test.pdf",
            created_by=agent.id,
        )
        doc = await doc_repo.create_from_create_schema(doc_create)

        # Now create ACL entry
        acl_create = DocumentACLCreate(
            document_id=doc.id,
            agent_id=agent.id,
            permission="READ",
            granted_by=granter.id,
        )

        # Create ACL entry
        acl = await acl_repo.create_from_create_schema(acl_create)
        assert acl.document_id == doc.id
        assert acl.agent_id == agent.id
        assert acl.permission == "READ"

        # Get by document
        acls = await acl_repo.get_by_document(doc.id)
        assert len(acls) == 1
        assert acls[0].permission == "READ"

        # Get by agent
        acls = await acl_repo.get_by_agent(agent.id)
        assert len(acls) == 1
        assert acls[0].permission == "READ"

        # Get by document and agent
        acls = await acl_repo.get_by_document_and_agent(doc.id, agent.id)
        assert len(acls) == 1
        assert acls[0].permission == "READ"

    @pytest.mark.asyncio
    async def test_check_permission(self, db_manager):
        """Test permission checking."""
        # Create prerequisite repositories
        org_repo = OrganizationRepository(db_manager)
        agent_repo = AgentRepository(db_manager)
        doc_repo = DocumentRepository(db_manager)
        acl_repo = ACLRepository(db_manager)

        # Create organization
        org_external_id = f"test-org-acl-check-{uuid4()}"
        org_create = OrganizationCreate(
            external_id=org_external_id,
            name="Test Organization for ACL Check",
        )
        org = await org_repo.create_from_create_schema(org_create)

        # Create agents
        agent_external_id = f"test-agent-acl-check-{uuid4()}"
        agent_create = AgentCreate(
            external_id=agent_external_id,
            organization_id=str(org.id),
            name="Test Agent for ACL Check",
        )
        agent = await agent_repo.create_from_create_schema(agent_create)

        granter_external_id = f"test-granter-acl-check-{uuid4()}"
        granted_by_create = AgentCreate(
            external_id=granter_external_id,
            organization_id=str(org.id),
            name="Test Granter for ACL Check",
        )
        granter = await agent_repo.create_from_create_schema(granted_by_create)

        # Create document
        doc_create = DocumentCreate(
            organization_id=org.id,
            name="Test Document for ACL Check",
            filename="test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            storage_path="test/path/test.pdf",
            created_by=agent.id,
            description="Test document for ACL check",
            tags=["test"],
            metadata={"test": True},
        )
        doc = await doc_repo.create_from_create_schema(doc_create)

        acl_create = DocumentACLCreate(
            document_id=doc.id,
            agent_id=agent.id,
            permission="READ",
            granted_by=granter.id,
        )
        await acl_repo.create_from_create_schema(acl_create)

        # Check permission
        has_permission = await acl_repo.check_permission(doc.id, agent.id, "READ")
        assert has_permission

        # Check non-existent permission
        has_permission = await acl_repo.check_permission(doc.id, agent.id, "WRITE")
        assert not has_permission

        # Check admin permission (should grant all)
        admin_acl_create = DocumentACLCreate(
            document_id=doc.id,
            agent_id=agent.id,
            permission="ADMIN",
            granted_by=granter.id,
        )
        await acl_repo.create_from_create_schema(admin_acl_create)

        has_permission = await acl_repo.check_permission(doc.id, agent.id, "WRITE")
        assert has_permission  # ADMIN grants WRITE

    @pytest.mark.asyncio
    async def test_update_acl(self, db_manager):
        """Test updating ACL entries."""
        # Create prerequisite repositories
        org_repo = OrganizationRepository(db_manager)
        agent_repo = AgentRepository(db_manager)
        doc_repo = DocumentRepository(db_manager)
        acl_repo = ACLRepository(db_manager)

        # Create organization
        org_external_id = f"test-org-acl-update-{uuid4()}"
        org_create = OrganizationCreate(
            external_id=org_external_id,
            name="Test Organization for ACL Update",
        )
        org = await org_repo.create_from_create_schema(org_create)

        # Create agents
        agent_external_id = f"test-agent-acl-update-{uuid4()}"
        agent_create = AgentCreate(
            external_id=agent_external_id,
            organization_id=str(org.id),
            name="Test Agent for ACL Update",
        )
        agent = await agent_repo.create_from_create_schema(agent_create)

        granter_external_id = f"test-granter-acl-update-{uuid4()}"
        granted_by_create = AgentCreate(
            external_id=granter_external_id,
            organization_id=str(org.id),
            name="Test Granter for ACL Update",
        )
        granter = await agent_repo.create_from_create_schema(granted_by_create)

        # Create document
        doc_create = DocumentCreate(
            organization_id=org.id,
            name="Test Document for ACL Update",
            filename="test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            storage_path="test/path/test.pdf",
            created_by=agent.id,
            description="Test document for ACL update",
            tags=["test"],
            metadata={"test": True},
        )
        doc = await doc_repo.create_from_create_schema(doc_create)

        acl_create = DocumentACLCreate(
            document_id=doc.id,
            agent_id=agent.id,
            permission="READ",
            granted_by=granter.id,
        )
        acl = await acl_repo.create_from_create_schema(acl_create)

        # Update permission
        updated_acl = await acl_repo.update(acl.id, {"permission": "WRITE"})
        assert updated_acl.permission == "WRITE"

    @pytest.mark.asyncio
    async def test_delete_acl(self, db_manager):
        """Test deleting ACL entries."""
        # Create prerequisite repositories
        org_repo = OrganizationRepository(db_manager)
        agent_repo = AgentRepository(db_manager)
        doc_repo = DocumentRepository(db_manager)
        acl_repo = ACLRepository(db_manager)

        # Create organization
        org_external_id = f"test-org-acl-delete-{uuid4()}"
        org_create = OrganizationCreate(
            external_id=org_external_id,
            name="Test Organization for ACL Delete",
        )
        org = await org_repo.create_from_create_schema(org_create)

        # Create agents
        agent_external_id = f"test-agent-acl-delete-{uuid4()}"
        agent_create = AgentCreate(
            external_id=agent_external_id,
            organization_id=str(org.id),
            name="Test Agent for ACL Delete",
        )
        agent = await agent_repo.create_from_create_schema(agent_create)

        granter_external_id = f"test-granter-acl-delete-{uuid4()}"
        granted_by_create = AgentCreate(
            external_id=granter_external_id,
            organization_id=str(org.id),
            name="Test Granter for ACL Delete",
        )
        granter = await agent_repo.create_from_create_schema(granted_by_create)

        # Create document
        doc_create = DocumentCreate(
            organization_id=org.id,
            name="Test Document for ACL Delete",
            filename="test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            storage_path="test/path/test.pdf",
            created_by=agent.id,
            description="Test document for ACL delete",
            tags=["test"],
            metadata={"test": True},
        )
        doc = await doc_repo.create_from_create_schema(doc_create)

        acl_create = DocumentACLCreate(
            document_id=doc.id,
            agent_id=agent.id,
            permission="READ",
            granted_by=granter.id,
        )
        acl = await acl_repo.create_from_create_schema(acl_create)

        # Delete ACL entry
        deleted = await acl_repo.delete(acl.id)
        assert deleted

        # Verify it's gone
        acls = await acl_repo.get_by_document(doc.id)
        assert len(acls) == 0

    @pytest.mark.asyncio
    async def test_revoke_permission(self, db_manager):
        """Test revoking specific permissions."""
        # Create prerequisite repositories
        org_repo = OrganizationRepository(db_manager)
        agent_repo = AgentRepository(db_manager)
        doc_repo = DocumentRepository(db_manager)
        acl_repo = ACLRepository(db_manager)

        # Create organization
        org_external_id = f"test-org-acl-revoke-{uuid4()}"
        org_create = OrganizationCreate(
            external_id=org_external_id,
            name="Test Organization for ACL Revoke",
        )
        org = await org_repo.create_from_create_schema(org_create)

        # Create agents
        agent_external_id = f"test-agent-acl-revoke-{uuid4()}"
        agent_create = AgentCreate(
            external_id=agent_external_id,
            organization_id=str(org.id),
            name="Test Agent for ACL Revoke",
        )
        agent = await agent_repo.create_from_create_schema(agent_create)

        granter_external_id = f"test-granter-acl-revoke-{uuid4()}"
        granted_by_create = AgentCreate(
            external_id=granter_external_id,
            organization_id=str(org.id),
            name="Test Granter for ACL Revoke",
        )
        granter = await agent_repo.create_from_create_schema(granted_by_create)

        # Create document
        doc_create = DocumentCreate(
            organization_id=org.id,
            name="Test Document for ACL Revoke",
            filename="test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            storage_path="test/path/test.pdf",
            created_by=agent.id,
            description="Test document for ACL revoke",
            tags=["test"],
            metadata={"test": True},
        )
        doc = await doc_repo.create_from_create_schema(doc_create)

        acl_create = DocumentACLCreate(
            document_id=doc.id,
            agent_id=agent.id,
            permission="READ",
            granted_by=granter.id,
        )
        await acl_repo.create_from_create_schema(acl_create)

        # Revoke permission
        revoked = await acl_repo.revoke_permission(doc.id, agent.id, "READ")
        assert revoked

        # Verify it's gone
        has_permission = await acl_repo.check_permission(doc.id, agent.id, "READ")
        assert not has_permission

    @pytest.mark.asyncio
    async def test_revoke_all_permissions(self, db_manager):
        """Test revoking all permissions for an agent on a document."""
        # Create prerequisite repositories
        org_repo = OrganizationRepository(db_manager)
        agent_repo = AgentRepository(db_manager)
        doc_repo = DocumentRepository(db_manager)
        acl_repo = ACLRepository(db_manager)

        # Create organization
        org_external_id = f"test-org-acl-revoke-all-{uuid4()}"
        org_create = OrganizationCreate(
            external_id=org_external_id,
            name="Test Organization for ACL Revoke All",
        )
        org = await org_repo.create_from_create_schema(org_create)

        # Create agents
        agent_external_id = f"test-agent-acl-revoke-all-{uuid4()}"
        agent_create = AgentCreate(
            external_id=agent_external_id,
            organization_id=str(org.id),
            name="Test Agent for ACL Revoke All",
        )
        agent = await agent_repo.create_from_create_schema(agent_create)

        granter_external_id = f"test-granter-acl-revoke-all-{uuid4()}"
        granted_by_create = AgentCreate(
            external_id=granter_external_id,
            organization_id=str(org.id),
            name="Test Granter for ACL Revoke All",
        )
        granter = await agent_repo.create_from_create_schema(granted_by_create)

        # Create document
        doc_create = DocumentCreate(
            organization_id=org.id,
            name="Test Document for ACL Revoke All",
            filename="test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            storage_path="test/path/test.pdf",
            created_by=agent.id,
            description="Test document for ACL revoke all",
            tags=["test"],
            metadata={"test": True},
        )
        doc = await doc_repo.create_from_create_schema(doc_create)

        # Create multiple permissions
        for permission in ["READ", "WRITE", "DELETE"]:
            acl_create = DocumentACLCreate(
                document_id=doc.id,
                agent_id=agent.id,
                permission=permission,
                granted_by=granter.id,
            )
            await acl_repo.create_from_create_schema(acl_create)

        # Verify permissions exist
        permissions = await acl_repo.get_agent_permissions(doc.id, agent.id)
        assert len(permissions) == 3

        # Revoke all permissions
        count = await acl_repo.revoke_all_permissions(doc.id, agent.id)
        assert count == 3

        # Verify all are gone
        permissions = await acl_repo.get_agent_permissions(doc.id, agent.id)
        assert len(permissions) == 0

    @pytest.mark.asyncio
    async def test_grant_permission_upsert(self, db_manager):
        """Test granting permission with upsert logic."""
        # Create prerequisite repositories
        org_repo = OrganizationRepository(db_manager)
        agent_repo = AgentRepository(db_manager)
        doc_repo = DocumentRepository(db_manager)
        acl_repo = ACLRepository(db_manager)

        # Create organization
        org_external_id = f"test-org-acl-grant-{uuid4()}"
        org_create = OrganizationCreate(
            external_id=org_external_id,
            name="Test Organization for ACL Grant",
        )
        org = await org_repo.create_from_create_schema(org_create)

        # Create agents
        agent_external_id = f"test-agent-acl-grant-{uuid4()}"
        agent_create = AgentCreate(
            external_id=agent_external_id,
            organization_id=str(org.id),
            name="Test Agent for ACL Grant",
        )
        agent = await agent_repo.create_from_create_schema(agent_create)

        granter_external_id = f"test-granter-acl-grant-{uuid4()}"
        granted_by_create = AgentCreate(
            external_id=granter_external_id,
            organization_id=str(org.id),
            name="Test Granter for ACL Grant",
        )
        granter = await agent_repo.create_from_create_schema(granted_by_create)

        # Create document
        doc_create = DocumentCreate(
            organization_id=org.id,
            name="Test Document for ACL Grant",
            filename="test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            storage_path="test/path/test.pdf",
            created_by=agent.id,
            description="Test document for ACL grant",
            tags=["test"],
            metadata={"test": True},
        )
        doc = await doc_repo.create_from_create_schema(doc_create)

        # Grant permission
        acl = await acl_repo.grant_permission(doc.id, agent.id, "READ", granter.id)
        assert acl.permission == "READ"

        # Grant same permission again (should update, not create duplicate)
        acl2 = await acl_repo.grant_permission(doc.id, agent.id, "READ", granter.id)
        assert acl2.id == acl.id  # Same record

        # Check we still have only one permission
        acls = await acl_repo.get_by_document_and_agent(doc.id, agent.id)
        assert len(acls) == 1
