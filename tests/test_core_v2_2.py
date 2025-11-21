"""
Integration tests for DocVault SDK v2.2 type-safe responses.

Tests all methods that return v2.2 response models:
- list_docs() → DocumentListResponse
- search() → SearchResponse
- get_document_details() → DocumentDetails
- get_permissions() → PermissionListResponse
- set_permissions() → List[DocumentACL]
- transfer_ownership() → OwnershipTransferResponse
"""

import pytest
from uuid import uuid4
import tempfile
from pathlib import Path

from doc_vault import DocVaultSDK
from doc_vault.database.schemas import (
    DocumentListResponse,
    SearchResponse,
    DocumentDetails,
    PermissionListResponse,
    OwnershipTransferResponse,
    PermissionGrant,
    PaginationMeta,
)
from doc_vault.exceptions import PermissionDeniedError


pytestmark = pytest.mark.asyncio


class TestListDocsTypeSafe:
    """Tests for list_docs() returning DocumentListResponse."""

    async def test_list_docs_returns_correct_type(
        self, vault_sdk, test_org, test_agent
    ):
        """Test that list_docs returns DocumentListResponse."""
        result = await vault_sdk.list_docs(
            organization_id=test_org.id, agent_id=test_agent.id
        )

        assert isinstance(result, DocumentListResponse)
        assert hasattr(result, "documents")
        assert hasattr(result, "pagination")
        assert hasattr(result, "filters")

    async def test_list_docs_pagination_metadata(
        self, vault_sdk, test_org, test_agent, sample_document
    ):
        """Test pagination metadata in DocumentListResponse."""
        result = await vault_sdk.list_docs(
            organization_id=test_org.id, agent_id=test_agent.id, limit=10, offset=0
        )

        assert isinstance(result.pagination, PaginationMeta)
        assert result.pagination.total >= 1  # At least our sample doc
        assert result.pagination.limit == 10
        assert result.pagination.offset == 0
        assert isinstance(result.pagination.has_more, bool)

    async def test_list_docs_documents_attribute(
        self, vault_sdk, test_org, test_agent, sample_document
    ):
        """Test accessing documents via model attribute."""
        result = await vault_sdk.list_docs(
            organization_id=test_org.id, agent_id=test_agent.id
        )

        # Should be able to iterate over documents
        for doc in result.documents:
            assert hasattr(doc, "id")
            assert hasattr(doc, "name")
            assert hasattr(doc, "status")

    async def test_list_docs_filters_attribute(self, vault_sdk, test_org, test_agent):
        """Test filters attribute in response."""
        result = await vault_sdk.list_docs(
            organization_id=test_org.id,
            agent_id=test_agent.id,
            status="active",
            tags=["test"],
        )

        assert isinstance(result.filters, dict)

    async def test_list_docs_serialization(self, vault_sdk, test_org, test_agent):
        """Test that response can be serialized to dict."""
        result = await vault_sdk.list_docs(
            organization_id=test_org.id, agent_id=test_agent.id
        )

        # Should be able to convert to dict
        data = result.model_dump()
        assert "documents" in data
        assert "pagination" in data
        assert "filters" in data


class TestSearchTypeSafe:
    """Tests for search() returning SearchResponse."""

    async def test_search_returns_correct_type(
        self, vault_sdk, test_org, test_agent, sample_document
    ):
        """Test that search returns SearchResponse."""
        result = await vault_sdk.search(
            query="test", organization_id=test_org.id, agent_id=test_agent.id
        )

        assert isinstance(result, SearchResponse)
        assert hasattr(result, "documents")
        assert hasattr(result, "query")
        assert hasattr(result, "pagination")
        assert hasattr(result, "filters")

    async def test_search_query_attribute(self, vault_sdk, test_org, test_agent):
        """Test query attribute in SearchResponse."""
        search_query = "financial report"
        result = await vault_sdk.search(
            query=search_query, organization_id=test_org.id, agent_id=test_agent.id
        )

        assert result.query == search_query

    async def test_search_pagination_metadata(self, vault_sdk, test_org, test_agent):
        """Test pagination in SearchResponse."""
        result = await vault_sdk.search(
            query="test", organization_id=test_org.id, agent_id=test_agent.id, limit=5
        )

        assert isinstance(result.pagination, PaginationMeta)
        assert result.pagination.limit == 5

    async def test_search_documents_access(
        self, vault_sdk, test_org, test_agent, sample_document
    ):
        """Test accessing search results via documents attribute."""
        result = await vault_sdk.search(
            query="sample", organization_id=test_org.id, agent_id=test_agent.id
        )

        # Should be iterable
        for doc in result.documents:
            assert hasattr(doc, "id")
            assert hasattr(doc, "name")


class TestGetDocumentDetailsTypeSafe:
    """Tests for get_document_details() returning DocumentDetails."""

    async def test_get_document_details_returns_correct_type(
        self, vault_sdk, test_agent, sample_document
    ):
        """Test that get_document_details returns DocumentDetails."""
        details = await vault_sdk.get_document_details(
            document_id=sample_document.id, agent_id=test_agent.id
        )

        assert isinstance(details, DocumentDetails)
        assert hasattr(details, "document")
        assert hasattr(details, "versions")
        assert hasattr(details, "permissions")
        assert hasattr(details, "version_count")
        assert hasattr(details, "current_version")

    async def test_get_document_details_document_attribute(
        self, vault_sdk, test_agent, sample_document
    ):
        """Test document attribute in DocumentDetails."""
        details = await vault_sdk.get_document_details(
            document_id=sample_document.id, agent_id=test_agent.id
        )

        assert details.document.id == sample_document.id
        assert details.document.name == sample_document.name

    async def test_get_document_details_version_metadata(
        self, vault_sdk, test_agent, sample_document
    ):
        """Test version metadata fields."""
        details = await vault_sdk.get_document_details(
            document_id=sample_document.id,
            agent_id=test_agent.id,
            include_versions=True,
        )

        assert isinstance(details.version_count, int)
        assert isinstance(details.current_version, int)
        assert details.version_count >= 1
        assert details.current_version >= 1

    async def test_get_document_details_with_versions(
        self, vault_sdk, test_agent, sample_document
    ):
        """Test versions attribute when requested."""
        details = await vault_sdk.get_document_details(
            document_id=sample_document.id,
            agent_id=test_agent.id,
            include_versions=True,
        )

        if details.versions:
            assert isinstance(details.versions, list)
            for version in details.versions:
                assert hasattr(version, "version_number")
                assert hasattr(version, "created_at")

    async def test_get_document_details_without_versions(
        self, vault_sdk, test_agent, sample_document
    ):
        """Test that versions is None when not requested."""
        details = await vault_sdk.get_document_details(
            document_id=sample_document.id,
            agent_id=test_agent.id,
            include_versions=False,
        )

        # versions should be None or empty when not requested
        assert details.versions is None or len(details.versions) == 0

    async def test_get_document_details_with_permissions_as_admin(
        self, vault_sdk, test_agent, sample_document
    ):
        """Test permissions attribute when requested by ADMIN."""
        # Owner (uploaded_by) should have ADMIN permission
        details = await vault_sdk.get_document_details(
            document_id=sample_document.id,
            agent_id=test_agent.id,  # Owner
            include_permissions=True,
        )

        # Should have permissions
        if details.permissions:
            assert isinstance(details.permissions, list)
            for perm in details.permissions:
                assert hasattr(perm, "agent_id")
                assert hasattr(perm, "permission")

    async def test_get_document_details_permissions_denied_for_non_admin(
        self, vault_sdk, test_org, test_agent, sample_document
    ):
        """Test that non-ADMIN users cannot view permissions."""
        # Create another agent without ADMIN permission
        other_agent_id = str(uuid4())
        other_agent = await vault_sdk.register_agent(
            agent_id=other_agent_id, organization_id=test_org.id
        )

        # Grant READ permission to other agent
        await vault_sdk.set_permissions(
            document_id=sample_document.id,
            permissions=[PermissionGrant(agent_id=other_agent.id, permission="READ")],
            granted_by=test_agent.id,
        )

        # Should raise PermissionDeniedError when requesting permissions
        with pytest.raises(PermissionDeniedError):
            await vault_sdk.get_document_details(
                document_id=sample_document.id,
                agent_id=other_agent.id,
                include_permissions=True,
            )


class TestGetPermissionsTypeSafe:
    """Tests for get_permissions() returning PermissionListResponse."""

    async def test_get_permissions_returns_correct_type(
        self, vault_sdk, test_agent, sample_document
    ):
        """Test that get_permissions returns PermissionListResponse."""
        result = await vault_sdk.get_permissions(document_id=sample_document.id)

        assert isinstance(result, PermissionListResponse)
        assert hasattr(result, "document_id")
        assert hasattr(result, "permissions")
        assert hasattr(result, "total")
        assert hasattr(result, "requested_by")
        assert hasattr(result, "requested_at")

    async def test_get_permissions_document_id(
        self, vault_sdk, test_agent, sample_document
    ):
        """Test document_id attribute."""
        result = await vault_sdk.get_permissions(document_id=sample_document.id)

        assert result.document_id == sample_document.id

    async def test_get_permissions_total_count(
        self, vault_sdk, test_agent, sample_document
    ):
        """Test total attribute."""
        result = await vault_sdk.get_permissions(document_id=sample_document.id)

        assert isinstance(result.total, int)
        assert result.total >= 0

    async def test_get_permissions_list_access(
        self, vault_sdk, test_agent, sample_document
    ):
        """Test accessing permissions list."""
        result = await vault_sdk.get_permissions(document_id=sample_document.id)

        assert isinstance(result.permissions, list)
        for acl in result.permissions:
            assert hasattr(acl, "agent_id")
            assert hasattr(acl, "permission")
            assert hasattr(acl, "granted_by")

    async def test_get_permissions_metadata_fields(
        self, vault_sdk, test_agent, sample_document
    ):
        """Test metadata fields in response."""
        result = await vault_sdk.get_permissions(
            document_id=sample_document.id, agent_id=test_agent.id
        )

        assert hasattr(result, "requested_by")
        assert hasattr(result, "requested_at")


class TestSetPermissionsTypeSafe:
    """Tests for set_permissions() with PermissionGrant models."""

    async def test_set_permissions_with_permission_grant(
        self, vault_sdk, test_org, test_agent, sample_document
    ):
        """Test set_permissions with PermissionGrant models."""
        other_agent_id = str(uuid4())
        other_agent = await vault_sdk.register_agent(
            agent_id=other_agent_id, organization_id=test_org.id
        )

        # Should accept List[PermissionGrant]
        result = await vault_sdk.set_permissions(
            document_id=sample_document.id,
            permissions=[PermissionGrant(agent_id=other_agent.id, permission="READ")],
            granted_by=test_agent.id,
        )

        assert isinstance(result, list)
        assert len(result) > 0
        # Each item should be DocumentACL
        for acl in result:
            assert hasattr(acl, "agent_id")
            assert hasattr(acl, "permission")

    async def test_set_permissions_multiple_grants(
        self, vault_sdk, test_org, test_agent, sample_document
    ):
        """Test setting multiple permissions at once."""
        agent1_id = str(uuid4())
        agent2_id = str(uuid4())

        agent1 = await vault_sdk.register_agent(
            agent_id=agent1_id, organization_id=test_org.id
        )
        agent2 = await vault_sdk.register_agent(
            agent_id=agent2_id, organization_id=test_org.id
        )

        result = await vault_sdk.set_permissions(
            document_id=sample_document.id,
            permissions=[
                PermissionGrant(agent_id=agent1.id, permission="READ"),
                PermissionGrant(agent_id=agent2.id, permission="WRITE"),
            ],
            granted_by=test_agent.id,
        )

        assert len(result) >= 2

    async def test_set_permissions_rejects_dict(
        self, vault_sdk, test_org, test_agent, sample_document
    ):
        """Test that dict format is rejected in v2.2."""
        other_agent_id = str(uuid4())
        await vault_sdk.register_agent(
            agent_id=other_agent_id, organization_id=test_org.id
        )

        # Dict format should raise TypeError (not Pydantic ValidationError)
        with pytest.raises((TypeError, AttributeError)):
            await vault_sdk.set_permissions(
                document_id=sample_document.id,
                permissions=[
                    {
                        "agent_id": other_agent_id,
                        "permission": "READ",
                    }  # Dict not allowed
                ],
                granted_by=test_agent.id,
            )


class TestTransferOwnershipTypeSafe:
    """Tests for transfer_ownership() returning OwnershipTransferResponse."""

    async def test_transfer_ownership_returns_correct_type(
        self, vault_sdk, test_org, test_agent, sample_document
    ):
        """Test that transfer_ownership returns OwnershipTransferResponse."""
        new_owner_id = str(uuid4())
        new_owner = await vault_sdk.register_agent(
            agent_id=new_owner_id, organization_id=test_org.id
        )

        result = await vault_sdk.transfer_ownership(
            document_id=sample_document.id,
            new_owner_id=new_owner.id,
            transferred_by=test_agent.id,
        )

        assert isinstance(result, OwnershipTransferResponse)
        assert hasattr(result, "document")
        assert hasattr(result, "old_owner")
        assert hasattr(result, "new_owner")
        assert hasattr(result, "transferred_by")
        assert hasattr(result, "transferred_at")
        assert hasattr(result, "new_permissions")

    async def test_transfer_ownership_metadata(
        self, vault_sdk, test_org, test_agent, sample_document
    ):
        """Test ownership transfer metadata fields."""
        new_owner_id = str(uuid4())
        new_owner = await vault_sdk.register_agent(
            agent_id=new_owner_id, organization_id=test_org.id
        )

        result = await vault_sdk.transfer_ownership(
            document_id=sample_document.id,
            new_owner_id=new_owner.id,
            transferred_by=test_agent.id,
        )

        assert result.old_owner == test_agent.id
        assert result.new_owner == new_owner.id
        assert result.transferred_by == test_agent.id
        assert result.transferred_at is not None

    async def test_transfer_ownership_new_permissions(
        self, vault_sdk, test_org, test_agent, sample_document
    ):
        """Test new_permissions attribute."""
        new_owner_id = str(uuid4())
        new_owner = await vault_sdk.register_agent(
            agent_id=new_owner_id, organization_id=test_org.id
        )

        result = await vault_sdk.transfer_ownership(
            document_id=sample_document.id,
            new_owner_id=new_owner.id,
            transferred_by=test_agent.id,
        )

        assert isinstance(result.new_permissions, list)
        # New owner should have ADMIN permission
        admin_perms = [
            p
            for p in result.new_permissions
            if p.permission == "ADMIN" and p.agent_id == new_owner.id
        ]
        assert len(admin_perms) > 0


# Fixtures


@pytest.fixture
async def vault_sdk():
    """Create a DocVaultSDK instance for testing."""
    async with DocVaultSDK() as vault:
        yield vault


@pytest.fixture
async def test_org(vault_sdk):
    """Create a test organization."""
    org_id = str(uuid4())
    org = await vault_sdk.register_organization(org_id=org_id, metadata={"test": True})
    return org


@pytest.fixture
async def test_agent(vault_sdk, test_org):
    """Create a test agent."""
    agent_id = str(uuid4())
    agent = await vault_sdk.register_agent(
        agent_id=agent_id, organization_id=test_org.id, metadata={"test": True}
    )
    return agent


@pytest.fixture
async def sample_document(vault_sdk, test_org, test_agent):
    """Create a sample document for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Sample document content for v2.2 tests")
        temp_path = f.name

    try:
        doc = await vault_sdk.upload(
            file_input=temp_path,
            name="Sample Document",
            organization_id=test_org.id,
            agent_id=test_agent.id,
            tags=["test", "sample"],
        )
        return doc
    finally:
        Path(temp_path).unlink(missing_ok=True)
