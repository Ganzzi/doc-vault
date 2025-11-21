"""
Tests for permission security features (v2.1).

Covers:
- Permission security gap fix (Issue #013)
- Only owners can view permissions in get_document_details()
"""

import pytest
from uuid import uuid4

from doc_vault.core import DocVaultSDK
from doc_vault.exceptions import PermissionDeniedError


pytestmark = pytest.mark.asyncio


class TestPermissionSecurity:
    """Test permission security features."""

    async def test_get_document_details_permissions_owner_only(
        self, vault: DocVaultSDK, org_id: str, owner_id: str, reader_id: str
    ):
        """Test that only owners (ADMIN permission) can view permissions."""
        # Upload document as owner
        doc = await vault.upload(
            file_input=b"Test document content",
            name="Security Test Doc",
            organization_id=org_id,
            agent_id=owner_id,
            description="Testing permission security",
        )

        # Owner can see permissions (has ADMIN by default)
        details = await vault.get_document_details(
            document_id=doc.id,
            agent_id=owner_id,
            include_permissions=True,
        )

        assert "permissions" in details
        assert len(details["permissions"]) >= 1  # At least owner's ADMIN permission
        assert any(
            p["agent_id"] == str(owner_id) and p["permission"] == "ADMIN"
            for p in details["permissions"]
        )

        # Grant READ permission to another agent
        await vault.set_permissions(
            document_id=doc.id,
            permissions=[{"agent_id": reader_id, "permission": "READ"}],
            granted_by=owner_id,
        )

        # Reader can access document
        reader_details = await vault.get_document_details(
            document_id=doc.id,
            agent_id=reader_id,
            include_permissions=False,  # Don't request permissions
        )
        assert reader_details["id"] == str(doc.id)
        assert "permissions" not in reader_details

        # Reader CANNOT view permissions (lacks ADMIN)
        with pytest.raises(
            PermissionDeniedError,
            match="Only document owners.*ADMIN permission.*can view permissions",
        ):
            await vault.get_document_details(
                document_id=doc.id,
                agent_id=reader_id,
                include_permissions=True,  # Security violation
            )

    async def test_get_document_details_permissions_write_not_sufficient(
        self, vault: DocVaultSDK, org_id: str, owner_id: str
    ):
        """Test that WRITE permission is not sufficient to view permissions."""
        writer_id = uuid4()

        # Register writer agent
        await vault.register_agent(
            agent_id=writer_id,
            organization_id=org_id,
            metadata={"name": "Writer Agent"},
        )

        # Upload document as owner
        doc = await vault.upload(
            file_input=b"Content",
            name="Write Test Doc",
            organization_id=org_id,
            agent_id=owner_id,
        )

        # Grant WRITE permission
        await vault.set_permissions(
            document_id=doc.id,
            permissions=[{"agent_id": writer_id, "permission": "WRITE"}],
            granted_by=owner_id,
        )

        # Writer can access document details
        details = await vault.get_document_details(
            document_id=doc.id,
            agent_id=writer_id,
            include_permissions=False,
        )
        assert details["id"] == str(doc.id)

        # Writer CANNOT view permissions (needs ADMIN)
        with pytest.raises(PermissionDeniedError):
            await vault.get_document_details(
                document_id=doc.id,
                agent_id=writer_id,
                include_permissions=True,
            )

    async def test_get_document_details_permissions_share_not_sufficient(
        self, vault: DocVaultSDK, org_id: str, owner_id: str
    ):
        """Test that SHARE permission is not sufficient to view permissions."""
        sharer_id = uuid4()

        # Register sharer agent
        await vault.register_agent(
            agent_id=sharer_id,
            organization_id=org_id,
            metadata={"name": "Sharer Agent"},
        )

        # Upload document
        doc = await vault.upload(
            file_input=b"Content",
            name="Share Test Doc",
            organization_id=org_id,
            agent_id=owner_id,
        )

        # Grant SHARE permission
        await vault.set_permissions(
            document_id=doc.id,
            permissions=[{"agent_id": sharer_id, "permission": "SHARE"}],
            granted_by=owner_id,
        )

        # Sharer CANNOT view permissions (needs ADMIN)
        with pytest.raises(PermissionDeniedError):
            await vault.get_document_details(
                document_id=doc.id,
                agent_id=sharer_id,
                include_permissions=True,
            )

    async def test_get_document_details_multiple_admins_can_view(
        self, vault: DocVaultSDK, org_id: str, owner_id: str
    ):
        """Test that multiple agents with ADMIN permission can all view permissions."""
        admin2_id = uuid4()

        # Register second admin
        await vault.register_agent(
            agent_id=admin2_id,
            organization_id=org_id,
            metadata={"name": "Second Admin"},
        )

        # Upload document
        doc = await vault.upload(
            file_input=b"Content",
            name="Multi Admin Doc",
            organization_id=org_id,
            agent_id=owner_id,
        )

        # Grant ADMIN to second agent
        await vault.set_permissions(
            document_id=doc.id,
            permissions=[{"agent_id": admin2_id, "permission": "ADMIN"}],
            granted_by=owner_id,
        )

        # Both owners can view permissions
        owner_details = await vault.get_document_details(
            document_id=doc.id,
            agent_id=owner_id,
            include_permissions=True,
        )
        assert "permissions" in owner_details

        admin2_details = await vault.get_document_details(
            document_id=doc.id,
            agent_id=admin2_id,
            include_permissions=True,
        )
        assert "permissions" in admin2_details

        # Both see the same permissions
        assert len(owner_details["permissions"]) == len(admin2_details["permissions"])
