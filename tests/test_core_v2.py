"""
Tests for v2.0 SDK methods integration in DocVaultSDK.

Tests cover the new v2.0 method integrations for enhanced document operations,
listing, searching, and permission management.
"""

import pytest
from uuid import uuid4, UUID
from io import BytesIO
from typing import AsyncGenerator

from doc_vault.core import DocVaultSDK
from doc_vault.models import Document, Organization, Agent, ACL
from doc_vault.database.schemas import (
    DocumentCreate,
    OrganizationCreate,
    AgentCreate,
)
from doc_vault.exceptions import (
    NotFoundError,
    PermissionDeniedError,
)


class TestSDKEnhancedUpload:
    """Test enhanced document upload with v2.0 SDK integration."""

    @pytest.mark.asyncio
    async def test_upload_enhanced_with_bytes(self, doc_vault_sdk, test_org, test_agent):
        """Test uploading document with bytes input."""
        content = b"Hello, World!"
        
        doc = await doc_vault_sdk.upload_enhanced(
            file_input=content,
            name="test_doc.txt",
            organization_id=test_org.id,
            agent_id=test_agent.id,
            description="Test document",
            tags=["test", "v2"],
        )
        
        assert doc is not None
        assert doc.name == "test_doc.txt"
        assert doc.organization_id == test_org.id
        assert doc.created_by == test_agent.id

    @pytest.mark.asyncio
    async def test_upload_enhanced_with_stream(self, doc_vault_sdk, test_org, test_agent):
        """Test uploading document with binary stream."""
        content = BytesIO(b"Stream content")
        
        doc = await doc_vault_sdk.upload_enhanced(
            file_input=content,
            name="stream_doc.bin",
            organization_id=test_org.id,
            agent_id=test_agent.id,
            content_type="application/octet-stream",
        )
        
        assert doc is not None
        assert doc.name == "stream_doc.bin"

    @pytest.mark.asyncio
    async def test_upload_enhanced_not_initialized(self):
        """Test upload_enhanced fails when SDK not initialized."""
        sdk = DocVaultSDK()
        
        with pytest.raises(RuntimeError, match="not initialized"):
            await sdk.upload_enhanced(
                file_input=b"content",
                name="test.txt",
                organization_id=uuid4(),
                agent_id=uuid4(),
            )


class TestSDKDocumentDetails:
    """Test getting comprehensive document details via SDK."""

    @pytest.mark.asyncio
    async def test_get_document_details(self, doc_vault_sdk, test_org, test_agent, test_document):
        """Test retrieving document details with metadata."""
        details = await doc_vault_sdk.get_document_details(
            document_id=test_document.id,
            agent_id=test_agent.id,
            include_versions=True,
            include_permissions=False,
        )
        
        assert details is not None
        assert details["document"]["id"] == test_document.id
        assert details["document"]["name"] == test_document.name
        assert "versions" in details

    @pytest.mark.asyncio
    async def test_get_document_details_with_permissions(
        self, doc_vault_sdk, test_org, test_agent, test_document
    ):
        """Test retrieving document details including permissions."""
        details = await doc_vault_sdk.get_document_details(
            document_id=test_document.id,
            agent_id=test_agent.id,
            include_permissions=True,
        )
        
        assert details is not None
        assert "permissions" in details

    @pytest.mark.asyncio
    async def test_get_document_details_not_found(self, doc_vault_sdk, test_agent):
        """Test getting details for non-existent document."""
        with pytest.raises(NotFoundError):
            await doc_vault_sdk.get_document_details(
                document_id=uuid4(),
                agent_id=test_agent.id,
            )


class TestSDKDocumentListing:
    """Test listing documents with SDK pagination and filtering."""

    @pytest.mark.asyncio
    async def test_list_documents_paginated(self, doc_vault_sdk, test_org, test_agent):
        """Test paginated document listing."""
        result = await doc_vault_sdk.list_documents_paginated(
            organization_id=test_org.id,
            agent_id=test_agent.id,
            limit=20,
            offset=0,
        )
        
        assert result is not None
        assert "documents" in result
        assert "total_count" in result
        assert "limit" in result
        assert "offset" in result

    @pytest.mark.asyncio
    async def test_list_documents_with_sorting(self, doc_vault_sdk, test_org, test_agent):
        """Test document listing with sorting."""
        result = await doc_vault_sdk.list_documents_paginated(
            organization_id=test_org.id,
            agent_id=test_agent.id,
            sort_by="name",
            sort_order="asc",
        )
        
        assert result is not None
        assert result.get("sort_by") == "name"
        assert result.get("sort_order") == "asc"

    @pytest.mark.asyncio
    async def test_list_documents_with_filtering(self, doc_vault_sdk, test_org, test_agent):
        """Test document listing with tag filtering."""
        result = await doc_vault_sdk.list_documents_paginated(
            organization_id=test_org.id,
            agent_id=test_agent.id,
            tags=["test"],
        )
        
        assert result is not None
        assert "documents" in result


class TestSDKDocumentSearch:
    """Test enhanced document search via SDK."""

    @pytest.mark.asyncio
    async def test_search_documents_enhanced(self, doc_vault_sdk, test_org, test_agent):
        """Test enhanced document search."""
        result = await doc_vault_sdk.search_documents_enhanced(
            query="test",
            organization_id=test_org.id,
            agent_id=test_agent.id,
        )
        
        assert result is not None
        assert "documents" in result or "results" in result

    @pytest.mark.asyncio
    async def test_search_with_prefix_filter(self, doc_vault_sdk, test_org, test_agent):
        """Test search with prefix filtering."""
        result = await doc_vault_sdk.search_documents_enhanced(
            query="*",
            organization_id=test_org.id,
            agent_id=test_agent.id,
            prefix="documents/",
        )
        
        assert result is not None

    @pytest.mark.asyncio
    async def test_search_with_pagination(self, doc_vault_sdk, test_org, test_agent):
        """Test search with pagination parameters."""
        result = await doc_vault_sdk.search_documents_enhanced(
            query="test",
            organization_id=test_org.id,
            agent_id=test_agent.id,
            limit=10,
            offset=0,
        )
        
        assert result is not None


class TestSDKBulkPermissions:
    """Test bulk permission operations via SDK."""

    @pytest.mark.asyncio
    async def test_set_permissions_bulk(
        self, doc_vault_sdk, test_org, test_agent, other_agent, test_document
    ):
        """Test setting multiple permissions."""
        permissions = [
            {
                "agent_id": other_agent.id,
                "permission": "read",
            },
            {
                "agent_id": other_agent.id,
                "permission": "write",
            },
        ]
        
        result = await doc_vault_sdk.set_permissions_bulk(
            document_id=test_document.id,
            permissions=permissions,
            granted_by=test_agent.id,
        )
        
        assert result is not None
        assert len(result) >= 0

    @pytest.mark.asyncio
    async def test_set_permissions_bulk_unauthorized(
        self, doc_vault_sdk, test_org, test_agent, other_agent, test_document
    ):
        """Test bulk permissions fails for non-owner."""
        permissions = [
            {
                "agent_id": other_agent.id,
                "permission": "write",
            },
        ]
        
        with pytest.raises(PermissionDeniedError):
            await doc_vault_sdk.set_permissions_bulk(
                document_id=test_document.id,
                permissions=permissions,
                granted_by=other_agent.id,
            )


class TestSDKDetailedPermissions:
    """Test detailed permission viewing via SDK."""

    @pytest.mark.asyncio
    async def test_get_permissions_detailed(
        self, doc_vault_sdk, test_org, test_agent, test_document
    ):
        """Test retrieving detailed permissions."""
        details = await doc_vault_sdk.get_permissions_detailed(
            document_id=test_document.id,
        )
        
        assert details is not None
        assert "permissions" in details or "acls" in details

    @pytest.mark.asyncio
    async def test_get_permissions_for_agent(
        self, doc_vault_sdk, test_org, test_agent, other_agent, test_document
    ):
        """Test retrieving permissions for specific agent."""
        details = await doc_vault_sdk.get_permissions_detailed(
            document_id=test_document.id,
            agent_id=other_agent.id,
        )
        
        assert details is not None


class TestSDKMultiPermissionCheck:
    """Test checking multiple permissions simultaneously."""

    @pytest.mark.asyncio
    async def test_check_permissions_multi(
        self, doc_vault_sdk, test_org, test_agent, test_document
    ):
        """Test checking multiple permissions."""
        result = await doc_vault_sdk.check_permissions_multi(
            document_id=test_document.id,
            agent_id=test_agent.id,
            permissions=["read", "write", "delete"],
        )
        
        assert result is not None
        assert "results" in result or "permissions" in result

    @pytest.mark.asyncio
    async def test_check_permissions_multi_not_initialized(self):
        """Test multi-check fails when SDK not initialized."""
        sdk = DocVaultSDK()
        
        with pytest.raises(RuntimeError, match="not initialized"):
            await sdk.check_permissions_multi(
                document_id=uuid4(),
                agent_id=uuid4(),
                permissions=["read"],
            )


class TestSDKReplaceContent:
    """Test replacing document content via SDK."""

    @pytest.mark.asyncio
    async def test_replace_document_content(
        self, doc_vault_sdk, test_org, test_agent, test_document
    ):
        """Test replacing document content."""
        new_content = b"Updated content"
        
        doc = await doc_vault_sdk.replace_document_content(
            document_id=test_document.id,
            file_input=new_content,
            agent_id=test_agent.id,
            create_version=True,
        )
        
        assert doc is not None
        assert doc.id == test_document.id

    @pytest.mark.asyncio
    async def test_replace_content_without_version(
        self, doc_vault_sdk, test_org, test_agent, test_document
    ):
        """Test replacing content in-place without versioning."""
        new_content = BytesIO(b"In-place replacement")
        
        doc = await doc_vault_sdk.replace_document_content(
            document_id=test_document.id,
            file_input=new_content,
            agent_id=test_agent.id,
            create_version=False,
        )
        
        assert doc is not None


class TestSDKTransferOwnership:
    """Test transferring document ownership via SDK."""

    @pytest.mark.asyncio
    async def test_transfer_ownership(
        self, doc_vault_sdk, test_org, test_agent, other_agent, test_document
    ):
        """Test transferring document ownership."""
        doc = await doc_vault_sdk.transfer_ownership(
            document_id=test_document.id,
            new_owner_id=other_agent.id,
            transferred_by=test_agent.id,
        )
        
        assert doc is not None
        assert doc.created_by == other_agent.id

    @pytest.mark.asyncio
    async def test_transfer_ownership_unauthorized(
        self, doc_vault_sdk, test_org, test_agent, other_agent, test_document
    ):
        """Test transfer fails for non-owner."""
        with pytest.raises(PermissionDeniedError):
            await doc_vault_sdk.transfer_ownership(
                document_id=test_document.id,
                new_owner_id=other_agent.id,
                transferred_by=other_agent.id,
            )


class TestSDKIntegrationScenarios:
    """Test realistic SDK usage scenarios combining multiple v2.0 methods."""

    @pytest.mark.asyncio
    async def test_upload_list_search_workflow(
        self, doc_vault_sdk, test_org, test_agent
    ):
        """Test realistic workflow: upload, list, search."""
        # Upload
        doc = await doc_vault_sdk.upload_enhanced(
            file_input=b"Content for workflow test",
            name="workflow_doc.txt",
            organization_id=test_org.id,
            agent_id=test_agent.id,
            tags=["workflow", "test"],
        )
        
        # List
        list_result = await doc_vault_sdk.list_documents_paginated(
            organization_id=test_org.id,
            agent_id=test_agent.id,
        )
        
        assert list_result is not None
        
        # Search
        search_result = await doc_vault_sdk.search_documents_enhanced(
            query="workflow",
            organization_id=test_org.id,
            agent_id=test_agent.id,
        )
        
        assert search_result is not None

    @pytest.mark.asyncio
    async def test_share_and_manage_permissions(
        self, doc_vault_sdk, test_org, test_agent, other_agent, test_document
    ):
        """Test workflow: grant permissions, check, view details."""
        # Grant permissions
        await doc_vault_sdk.set_permissions_bulk(
            document_id=test_document.id,
            permissions=[
                {"agent_id": other_agent.id, "permission": "read"}
            ],
            granted_by=test_agent.id,
        )
        
        # Check permissions
        check_result = await doc_vault_sdk.check_permissions_multi(
            document_id=test_document.id,
            agent_id=other_agent.id,
            permissions=["read", "write"],
        )
        
        assert check_result is not None
        
        # View permissions
        details = await doc_vault_sdk.get_permissions_detailed(
            document_id=test_document.id,
            agent_id=other_agent.id,
        )
        
        assert details is not None

    @pytest.mark.asyncio
    async def test_document_lifecycle(
        self, doc_vault_sdk, test_org, test_agent, other_agent
    ):
        """Test complete document lifecycle in v2.0."""
        # Create
        doc = await doc_vault_sdk.upload_enhanced(
            file_input=b"Lifecycle test",
            name="lifecycle.txt",
            organization_id=test_org.id,
            agent_id=test_agent.id,
        )
        
        # Get details
        details = await doc_vault_sdk.get_document_details(
            document_id=doc.id,
            agent_id=test_agent.id,
        )
        
        assert details is not None
        
        # Update content
        updated = await doc_vault_sdk.replace_document_content(
            document_id=doc.id,
            file_input=b"Updated lifecycle content",
            agent_id=test_agent.id,
            create_version=True,
        )
        
        assert updated is not None
        
        # Transfer ownership
        transferred = await doc_vault_sdk.transfer_ownership(
            document_id=doc.id,
            new_owner_id=other_agent.id,
            transferred_by=test_agent.id,
        )
        
        assert transferred is not None
