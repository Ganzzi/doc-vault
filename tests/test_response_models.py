"""
Tests for v2.2 response models.

Tests all response models introduced in v2.2:
- PaginationMeta
- DocumentListResponse
- SearchResponse
- DocumentDetails
- PermissionListResponse
- OwnershipTransferResponse
"""

import pytest
from datetime import datetime
from uuid import uuid4
from pydantic import ValidationError

from doc_vault.database.schemas import (
    PaginationMeta,
    DocumentListResponse,
    SearchResponse,
    DocumentDetails,
    PermissionListResponse,
    OwnershipTransferResponse,
    Document,
    DocumentVersion,
    DocumentACL,
)


class TestPaginationMeta:
    """Tests for PaginationMeta model."""

    def test_pagination_meta_instantiation(self):
        """Test creating a PaginationMeta instance."""
        meta = PaginationMeta(total=100, limit=10, offset=0, has_more=True)

        assert meta.total == 100
        assert meta.limit == 10
        assert meta.offset == 0
        assert meta.has_more is True

    def test_pagination_meta_has_more_calculation(self):
        """Test has_more flag logic."""
        # Has more
        meta = PaginationMeta(total=100, limit=10, offset=0, has_more=True)
        assert meta.has_more is True

        # No more
        meta = PaginationMeta(total=100, limit=10, offset=90, has_more=False)
        assert meta.has_more is False

    def test_pagination_meta_serialization(self):
        """Test model_dump() serialization."""
        meta = PaginationMeta(total=50, limit=20, offset=10, has_more=True)
        data = meta.model_dump()

        assert data["total"] == 50
        assert data["limit"] == 20
        assert data["offset"] == 10
        assert data["has_more"] is True

    def test_pagination_meta_validation(self):
        """Test field validation."""
        # Valid
        PaginationMeta(total=10, limit=5, offset=0, has_more=True)

        # Missing required field should fail
        with pytest.raises(ValidationError):
            PaginationMeta(total=10, limit=5)  # Missing offset and has_more


class TestDocumentListResponse:
    """Tests for DocumentListResponse model."""

    def test_document_list_response_empty(self):
        """Test with empty document list."""
        pagination = PaginationMeta(total=0, limit=10, offset=0, has_more=False)
        response = DocumentListResponse(documents=[], pagination=pagination, filters={})

        assert len(response.documents) == 0
        assert response.pagination.total == 0
        assert response.filters == {}

    def test_document_list_response_with_documents(self):
        """Test with multiple documents."""
        doc_id = uuid4()
        org_id = uuid4()
        agent_id = uuid4()

        doc = Document(
            id=doc_id,
            name="Test Doc",
            filename="test.txt",
            organization_id=org_id,
            created_by=agent_id,
            file_size=1024,
            storage_path="/test/path",
            current_version=1,
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        pagination = PaginationMeta(total=1, limit=10, offset=0, has_more=False)
        response = DocumentListResponse(
            documents=[doc], pagination=pagination, filters={"status": "active"}
        )

        assert len(response.documents) == 1
        assert response.documents[0].name == "Test Doc"
        assert response.pagination.total == 1
        assert response.filters["status"] == "active"

    def test_document_list_response_serialization(self):
        """Test serialization to dict."""
        pagination = PaginationMeta(total=0, limit=10, offset=0, has_more=False)
        response = DocumentListResponse(
            documents=[], pagination=pagination, filters={"tag": "test"}
        )

        data = response.model_dump()
        assert "documents" in data
        assert "pagination" in data
        assert "filters" in data
        assert data["pagination"]["total"] == 0


class TestSearchResponse:
    """Tests for SearchResponse model."""

    def test_search_response_basic(self):
        """Test basic search response."""
        pagination = PaginationMeta(total=5, limit=20, offset=0, has_more=False)
        response = SearchResponse(
            documents=[], query="test search", pagination=pagination, filters={}
        )

        assert response.query == "test search"
        assert response.pagination.total == 5
        assert len(response.documents) == 0

    def test_search_response_with_results(self):
        """Test search response with results."""
        doc_id = uuid4()
        org_id = uuid4()
        agent_id = uuid4()

        doc = Document(
            id=doc_id,
            name="Search Result",
            filename="search.txt",
            organization_id=org_id,
            created_by=agent_id,
            file_size=2048,
            storage_path="/search/result",
            current_version=1,
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        pagination = PaginationMeta(total=1, limit=20, offset=0, has_more=False)
        response = SearchResponse(
            documents=[doc],
            query="search term",
            pagination=pagination,
            filters={"prefix": "/docs"},
        )

        assert response.query == "search term"
        assert len(response.documents) == 1
        assert response.documents[0].name == "Search Result"
        assert response.filters["prefix"] == "/docs"

    def test_search_response_serialization(self):
        """Test serialization."""
        pagination = PaginationMeta(total=0, limit=20, offset=0, has_more=False)
        response = SearchResponse(
            documents=[], query="my query", pagination=pagination, filters={}
        )

        data = response.model_dump()
        assert data["query"] == "my query"
        assert "pagination" in data
        assert "documents" in data


class TestDocumentDetails:
    """Tests for DocumentDetails model."""

    def test_document_details_minimal(self):
        """Test DocumentDetails without optional fields."""
        doc_id = uuid4()
        org_id = uuid4()
        agent_id = uuid4()

        doc = Document(
            id=doc_id,
            name="Detail Doc",
            filename="detail.txt",
            organization_id=org_id,
            created_by=agent_id,
            file_size=512,
            storage_path="/detail/path",
            current_version=2,
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        details = DocumentDetails(
            document=doc,
            versions=None,
            permissions=None,
            version_count=2,
            current_version=2,
        )

        assert details.document.name == "Detail Doc"
        assert details.versions is None
        assert details.permissions is None
        assert details.version_count == 2
        assert details.current_version == 2

    def test_document_details_with_versions(self):
        """Test DocumentDetails with version history."""
        doc_id = uuid4()
        org_id = uuid4()
        agent_id = uuid4()

        doc = Document(
            id=doc_id,
            name="Versioned Doc",
            filename="versioned.txt",
            organization_id=org_id,
            created_by=agent_id,
            file_size=1024,
            storage_path="/versioned/path",
            current_version=2,
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        version1 = DocumentVersion(
            id=uuid4(),
            document_id=doc_id,
            version_number=1,
            filename="versioned_v1.txt",
            file_size=512,
            storage_path="/v1/path",
            created_by=agent_id,
            created_at=datetime.utcnow(),
        )

        version2 = DocumentVersion(
            id=uuid4(),
            document_id=doc_id,
            version_number=2,
            filename="versioned_v2.txt",
            file_size=1024,
            storage_path="/v2/path",
            created_by=agent_id,
            created_at=datetime.utcnow(),
            change_description="Updated content",
        )

        details = DocumentDetails(
            document=doc,
            versions=[version1, version2],
            permissions=None,
            version_count=2,
            current_version=2,
        )

        assert len(details.versions) == 2
        assert details.versions[0].version_number == 1
        assert details.versions[1].version_number == 2
        assert details.versions[1].change_description == "Updated content"

    def test_document_details_with_permissions(self):
        """Test DocumentDetails with permissions (ADMIN only)."""
        doc_id = uuid4()
        org_id = uuid4()
        agent_id = uuid4()

        doc = Document(
            id=doc_id,
            name="Protected Doc",
            filename="protected.txt",
            organization_id=org_id,
            created_by=agent_id,
            file_size=2048,
            storage_path="/protected/path",
            current_version=1,
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        acl = DocumentACL(
            id=uuid4(),
            document_id=doc_id,
            agent_id=agent_id,
            permission="ADMIN",
            granted_by=agent_id,
            granted_at=datetime.utcnow(),
        )

        details = DocumentDetails(
            document=doc,
            versions=None,
            permissions=[acl],
            version_count=1,
            current_version=1,
        )

        assert details.permissions is not None
        assert len(details.permissions) == 1
        assert details.permissions[0].permission == "ADMIN"

    def test_document_details_serialization(self):
        """Test serialization."""
        doc_id = uuid4()
        org_id = uuid4()
        agent_id = uuid4()

        doc = Document(
            id=doc_id,
            name="Serializable Doc",
            filename="serial.txt",
            organization_id=org_id,
            created_by=agent_id,
            file_size=128,
            storage_path="/serial/path",
            current_version=1,
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        details = DocumentDetails(
            document=doc,
            versions=None,
            permissions=None,
            version_count=1,
            current_version=1,
        )

        data = details.model_dump()
        assert "document" in data
        assert "version_count" in data
        assert "current_version" in data
        assert data["version_count"] == 1


class TestPermissionListResponse:
    """Tests for PermissionListResponse model."""

    def test_permission_list_response_empty(self):
        """Test with no permissions."""
        doc_id = uuid4()
        response = PermissionListResponse(
            document_id=doc_id,
            permissions=[],
            total=0,
            requested_by=None,
            requested_at=datetime.utcnow(),
        )

        assert response.document_id == doc_id
        assert len(response.permissions) == 0
        assert response.total == 0
        assert response.requested_by is None

    def test_permission_list_response_with_permissions(self):
        """Test with multiple permissions."""
        doc_id = uuid4()
        agent1_id = uuid4()
        agent2_id = uuid4()
        admin_id = uuid4()

        acl1 = DocumentACL(
            id=uuid4(),
            document_id=doc_id,
            agent_id=agent1_id,
            permission="READ",
            granted_by=admin_id,
            granted_at=datetime.utcnow(),
        )

        acl2 = DocumentACL(
            id=uuid4(),
            document_id=doc_id,
            agent_id=agent2_id,
            permission="WRITE",
            granted_by=admin_id,
            granted_at=datetime.utcnow(),
        )

        response = PermissionListResponse(
            document_id=doc_id,
            permissions=[acl1, acl2],
            total=2,
            requested_by=admin_id,
            requested_at=datetime.utcnow(),
        )

        assert response.document_id == doc_id
        assert len(response.permissions) == 2
        assert response.total == 2
        assert response.requested_by == admin_id
        assert response.permissions[0].permission == "READ"
        assert response.permissions[1].permission == "WRITE"

    def test_permission_list_response_serialization(self):
        """Test serialization."""
        doc_id = uuid4()
        response = PermissionListResponse(
            document_id=doc_id,
            permissions=[],
            total=0,
            requested_by=None,
            requested_at=datetime.utcnow(),
        )

        data = response.model_dump()
        assert "document_id" in data
        assert "permissions" in data
        assert "total" in data
        assert "requested_at" in data


class TestOwnershipTransferResponse:
    """Tests for OwnershipTransferResponse model."""

    def test_ownership_transfer_response(self):
        """Test ownership transfer response."""
        doc_id = uuid4()
        org_id = uuid4()
        old_owner = uuid4()
        new_owner = uuid4()
        admin_id = uuid4()

        doc = Document(
            id=doc_id,
            name="Transferred Doc",
            filename="transferred.txt",
            organization_id=org_id,
            created_by=new_owner,
            file_size=1024,
            storage_path="/transferred/path",
            current_version=1,
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # New owner gets ADMIN permission
        new_acl = DocumentACL(
            id=uuid4(),
            document_id=doc_id,
            agent_id=new_owner,
            permission="ADMIN",
            granted_by=admin_id,
            granted_at=datetime.utcnow(),
        )

        response = OwnershipTransferResponse(
            document=doc,
            old_owner=old_owner,
            new_owner=new_owner,
            transferred_by=admin_id,
            transferred_at=datetime.utcnow(),
            new_permissions=[new_acl],
        )

        assert response.document.name == "Transferred Doc"
        assert response.old_owner == old_owner
        assert response.new_owner == new_owner
        assert response.transferred_by == admin_id
        assert len(response.new_permissions) == 1
        assert response.new_permissions[0].agent_id == new_owner
        assert response.new_permissions[0].permission == "ADMIN"

    def test_ownership_transfer_response_serialization(self):
        """Test serialization."""
        doc_id = uuid4()
        org_id = uuid4()
        old_owner = uuid4()
        new_owner = uuid4()

        doc = Document(
            id=doc_id,
            name="Transfer Test",
            filename="transfer.txt",
            organization_id=org_id,
            created_by=new_owner,
            file_size=512,
            storage_path="/transfer/path",
            current_version=1,
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        response = OwnershipTransferResponse(
            document=doc,
            old_owner=old_owner,
            new_owner=new_owner,
            transferred_by=old_owner,
            transferred_at=datetime.utcnow(),
            new_permissions=[],
        )

        data = response.model_dump()
        assert "document" in data
        assert "old_owner" in data
        assert "new_owner" in data
        assert "transferred_by" in data
        assert "transferred_at" in data
        assert "new_permissions" in data
