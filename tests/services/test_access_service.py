"""
Integration tests for AccessService.

Tests access control functionality including granting/revoking permissions
and checking permissions.
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4, UUID

from doc_vault.exceptions import (
    DocumentNotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from doc_vault.services.access_service import AccessService


class TestAccessService:
    """Integration tests for AccessService."""

    @pytest.mark.asyncio
    async def test_grant_access_success(
        self,
        access_service: AccessService,
        db_manager,
        test_org: str,
        test_agent: str,
        test_document: str,
    ):
        """Test successful permission granting."""
        # Create another agent to grant access to
        from doc_vault.database.repositories.agent import AgentRepository
        from doc_vault.database.schemas.agent import AgentCreate

        agent_repo = AgentRepository(db_manager)
        grantee_id = str(uuid4())
        grantee_create = AgentCreate(
            external_id=grantee_id,
            organization_id=test_org,
            name="Grantee Agent",
            email="grantee@example.com",
            agent_type="human",
        )
        grantee = await agent_repo.create_from_create_schema(grantee_create)

        # Act - grant READ permission
        acl = await access_service.grant_access(
            document_id=test_document,
            agent_id=str(grantee.id),
            permission="READ",
            granted_by=test_agent,
        )

        # Assert
        assert acl.document_id == UUID(test_document)
        assert acl.agent_id == grantee.id
        assert acl.permission == "READ"
        assert acl.granted_by == UUID(test_agent)

    @pytest.mark.asyncio
    async def test_grant_access_invalid_permission(
        self,
        access_service: AccessService,
        test_document: str,
        test_agent: str,
    ):
        """Test granting invalid permission."""
        with pytest.raises(ValidationError, match="Invalid permission 'INVALID'"):
            await access_service.grant_access(
                document_id=test_document,
                agent_id=test_agent,
                permission="INVALID",
                granted_by=test_agent,
            )

    @pytest.mark.asyncio
    async def test_grant_access_no_share_permission(
        self,
        access_service: AccessService,
        db_manager,
        test_org: str,
        test_document: str,
    ):
        """Test granting access without SHARE permission."""
        # Create agent without SHARE permission
        from doc_vault.database.repositories.agent import AgentRepository
        from doc_vault.database.schemas.agent import AgentCreate

        agent_repo = AgentRepository(db_manager)
        unauthorized_id = str(uuid4())
        unauthorized_create = AgentCreate(
            external_id=unauthorized_id,
            organization_id=test_org,
            name="Unauthorized Agent",
            email="unauthorized@example.com",
            agent_type="human",
        )
        unauthorized = await agent_repo.create_from_create_schema(unauthorized_create)

        # Create another agent to grant access to
        grantee_id = str(uuid4())
        grantee_create = AgentCreate(
            external_id=grantee_id,
            organization_id=test_org,
            name="Grantee Agent 2",
            email="grantee2@example.com",
            agent_type="human",
        )
        grantee = await agent_repo.create_from_create_schema(grantee_create)

        with pytest.raises(
            PermissionDeniedError, match="does not have permission to share"
        ):
            await access_service.grant_access(
                document_id=test_document,
                agent_id=str(grantee.id),
                permission="READ",
                granted_by=str(unauthorized.id),
            )

    @pytest.mark.asyncio
    async def test_revoke_access_success(
        self,
        access_service: AccessService,
        db_manager,
        test_org: str,
        test_agent: str,
        test_document: str,
    ):
        """Test successful permission revocation."""
        # First grant permission
        from doc_vault.database.repositories.agent import AgentRepository
        from doc_vault.database.schemas.agent import AgentCreate

        agent_repo = AgentRepository(db_manager)
        revoke_target_id = str(uuid4())
        revoke_target_create = AgentCreate(
            external_id=revoke_target_id,
            organization_id=test_org,
            name="Revoke Target",
            email="revoke@example.com",
            agent_type="human",
        )
        revoke_target = await agent_repo.create_from_create_schema(revoke_target_create)

        # Grant permission first
        await access_service.grant_access(
            document_id=test_document,
            agent_id=str(revoke_target.id),
            permission="READ",
            granted_by=test_agent,
        )

        # Verify permission exists
        has_permission = await access_service.check_permission(
            document_id=test_document,
            agent_id=str(revoke_target.id),
            permission="READ",
        )
        assert has_permission is True

        # Act - revoke permission
        await access_service.revoke_access(
            document_id=test_document,
            agent_id=str(revoke_target.id),
            permission="READ",
            revoked_by=test_agent,
        )

        # Assert - permission should be gone
        has_permission = await access_service.check_permission(
            document_id=test_document,
            agent_id=str(revoke_target.id),
            permission="READ",
        )
        assert has_permission is False

    @pytest.mark.asyncio
    async def test_check_permission_success(
        self,
        access_service: AccessService,
        test_document: str,
        test_agent: str,
    ):
        """Test permission checking."""
        # Document creator should have ADMIN permission
        has_admin = await access_service.check_permission(
            document_id=test_document,
            agent_id=test_agent,
            permission="ADMIN",
        )
        assert has_admin is True

        # Should also have READ permission
        has_read = await access_service.check_permission(
            document_id=test_document,
            agent_id=test_agent,
            permission="READ",
        )
        assert has_read is True

    @pytest.mark.asyncio
    async def test_check_permission_no_access(
        self,
        access_service: AccessService,
        db_manager,
        test_org: str,
        test_document: str,
    ):
        """Test permission checking for agent without access."""
        # Create agent without any permissions
        from doc_vault.database.repositories.agent import AgentRepository
        from doc_vault.database.schemas.agent import AgentCreate

        agent_repo = AgentRepository(db_manager)
        no_access_id = str(uuid4())
        no_access_create = AgentCreate(
            external_id=no_access_id,
            organization_id=test_org,
            name="No Access Agent",
            email="noaccess@example.com",
            agent_type="human",
        )
        no_access = await agent_repo.create_from_create_schema(no_access_create)

        # Check permission
        has_access = await access_service.check_permission(
            document_id=test_document,
            agent_id=str(no_access.id),
            permission="READ",
        )
        assert has_access is False

    @pytest.mark.asyncio
    async def test_list_accessible_documents(
        self,
        access_service: AccessService,
        db_manager,
        test_org: str,
        test_agent: str,
        test_document: str,
    ):
        """Test listing accessible documents."""
        # Act
        accessible_docs = await access_service.list_accessible_documents(
            agent_id=test_agent,
            organization_id=test_org,
            permission="READ",
        )

        # Assert
        assert len(accessible_docs) >= 1
        assert any(doc.id == UUID(test_document) for doc in accessible_docs)

    @pytest.mark.asyncio
    async def test_list_accessible_documents_no_access(
        self,
        access_service: AccessService,
        db_manager,
        test_org: str,
    ):
        """Test listing accessible documents for agent with no access."""
        # Create agent in different organization
        from doc_vault.database.repositories.organization import OrganizationRepository
        from doc_vault.database.repositories.agent import AgentRepository
        from doc_vault.database.schemas.organization import OrganizationCreate
        from doc_vault.database.schemas.agent import AgentCreate

        org_repo = OrganizationRepository(db_manager)
        agent_repo = AgentRepository(db_manager)

        # Create different organization
        other_org_id = str(uuid4())
        other_org_create = OrganizationCreate(
            external_id=other_org_id,
            name="Other Organization",
        )
        other_org = await org_repo.create_from_create_schema(other_org_create)

        # Create agent in other organization
        other_agent_id = str(uuid4())
        other_agent_create = AgentCreate(
            external_id=other_agent_id,
            organization_id=str(other_org.id),
            name="Other Agent",
            email="other@example.com",
            agent_type="human",
        )
        other_agent = await agent_repo.create_from_create_schema(other_agent_create)

        # Act
        accessible_docs = await access_service.list_accessible_documents(
            agent_id=str(other_agent.id),
            organization_id=str(other_org.id),
            permission="READ",
        )

        # Assert - should have no accessible documents
        assert len(accessible_docs) == 0

    @pytest.mark.asyncio
    async def test_get_document_permissions(
        self,
        access_service: AccessService,
        test_document: str,
        test_agent: str,
    ):
        """Test getting document permissions."""
        # Act
        permissions = await access_service.get_document_permissions(
            document_id=test_document,
            agent_id=test_agent,
        )

        # Assert
        assert len(permissions) >= 1
        # Should include the creator's ADMIN permission
        admin_permissions = [p for p in permissions if p.permission == "ADMIN"]
        assert len(admin_permissions) >= 1

    @pytest.mark.asyncio
    async def test_grant_access_with_expiration(
        self,
        access_service: AccessService,
        db_manager,
        test_org: str,
        test_agent: str,
        test_document: str,
    ):
        """Test granting access with expiration."""
        # Create agent to grant access to
        from doc_vault.database.repositories.agent import AgentRepository
        from doc_vault.database.schemas.agent import AgentCreate

        agent_repo = AgentRepository(db_manager)
        temp_access_id = str(uuid4())
        temp_access_create = AgentCreate(
            external_id=temp_access_id,
            organization_id=test_org,
            name="Temp Access Agent",
            email="temp@example.com",
            agent_type="human",
        )
        temp_access = await agent_repo.create_from_create_schema(temp_access_create)

        # Set expiration to 1 hour from now
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        # Act - grant permission with expiration
        acl = await access_service.grant_access(
            document_id=test_document,
            agent_id=str(temp_access.id),
            permission="READ",
            granted_by=test_agent,
            expires_at=expires_at,
        )

        # Assert
        assert acl.expires_at is not None
        # Compare datetimes ignoring timezone and microseconds
        assert acl.expires_at.replace(microsecond=0) == expires_at.replace(
            tzinfo=None, microsecond=0
        )

        # Should have permission now
        has_permission = await access_service.check_permission(
            document_id=test_document,
            agent_id=str(temp_access.id),
            permission="READ",
        )
        assert has_permission is True
