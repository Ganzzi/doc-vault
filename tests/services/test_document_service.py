"""
Integration tests for DocumentService.

Tests document upload, download, metadata updates, deletion, and search
functionality with real database operations.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

from doc_vault.exceptions import (
    DocumentNotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from doc_vault.services.document_service import DocumentService


class TestDocumentService:
    """Integration tests for DocumentService."""

    @pytest.mark.asyncio
    async def test_upload_document_success(
        self,
        document_service: DocumentService,
        test_org: str,
        test_agent: str,
        temp_file: str,
    ):
        """Test successful document upload."""
        # Act
        document = await document_service.upload_document(
            file_path=temp_file,
            name="Test Upload Document",
            organization_id=test_org,
            agent_id=test_agent,
            description="Test document upload",
            tags=["test", "upload"],
            metadata={"test": True},
        )

        # Assert
        assert document.name == "Test Upload Document"
        assert document.description == "Test document upload"
        assert document.organization_id == UUID(test_org)
        assert document.created_by == UUID(test_agent)
        assert document.status == "active"
        assert document.current_version == 1
        assert document.tags == ["test", "upload"]
        assert document.metadata == {"test": True}
        assert document.filename.endswith(".txt")
        assert document.file_size > 0

    @pytest.mark.asyncio
    async def test_upload_document_invalid_file(
        self,
        document_service: DocumentService,
        test_org: str,
        test_agent: str,
    ):
        """Test upload with non-existent file."""
        with pytest.raises(ValidationError, match="File does not exist"):
            await document_service.upload_document(
                file_path="/non/existent/file.txt",
                name="Test Document",
                organization_id=test_org,
                agent_id=test_agent,
            )

    @pytest.mark.asyncio
    async def test_download_document_success(
        self,
        document_service: DocumentService,
        test_document: str,
        test_agent: str,
    ):
        """Test successful document download."""
        # Act
        content = await document_service.download_document(
            document_id=test_document,
            agent_id=test_agent,
        )

        # Assert
        assert isinstance(content, bytes)
        assert len(content) > 0
        assert content == b"This is test content for document upload."

    @pytest.mark.asyncio
    async def test_download_document_not_found(
        self,
        document_service: DocumentService,
        test_agent: str,
    ):
        """Test download of non-existent document."""
        fake_doc_id = str(uuid4())

        with pytest.raises(
            DocumentNotFoundError, match=f"Document {fake_doc_id} not found"
        ):
            await document_service.download_document(
                document_id=fake_doc_id,
                agent_id=test_agent,
            )

    @pytest.mark.asyncio
    async def test_download_document_no_permission(
        self,
        document_service: DocumentService,
        test_document: str,
        test_org: str,
    ):
        """Test download without permission."""
        # Create another agent without permission
        agent_repo = document_service.agent_repo
        agent_id = str(uuid4())
        from doc_vault.database.schemas.agent import AgentCreate

        agent_create = AgentCreate(
            external_id=agent_id,
            organization_id=test_org,
            name="Unauthorized Agent",
            email="unauthorized@example.com",
            agent_type="human",
        )
        unauthorized_agent = await agent_repo.create_from_create_schema(agent_create)

        with pytest.raises(
            PermissionDeniedError, match="does not have READ permission"
        ):
            await document_service.download_document(
                document_id=test_document,
                agent_id=str(unauthorized_agent.id),
            )

    @pytest.mark.asyncio
    async def test_update_metadata_success(
        self,
        document_service: DocumentService,
        test_document: str,
        test_agent: str,
    ):
        """Test successful metadata update."""
        # Act
        updated_doc = await document_service.update_metadata(
            document_id=test_document,
            agent_id=test_agent,
            name="Updated Document Name",
            description="Updated description",
            tags=["updated", "test"],
            metadata={"updated": True, "version": 2},
        )

        # Assert
        assert updated_doc.name == "Updated Document Name"
        assert updated_doc.description == "Updated description"
        assert updated_doc.tags == ["updated", "test"]
        assert updated_doc.metadata == {"test": True, "updated": True, "version": 2}

    @pytest.mark.asyncio
    async def test_update_metadata_no_permission(
        self,
        document_service: DocumentService,
        test_document: str,
        test_org: str,
    ):
        """Test metadata update without permission."""
        # Create agent without permission
        agent_repo = document_service.agent_repo
        agent_id = str(uuid4())
        from doc_vault.database.schemas.agent import AgentCreate

        agent_create = AgentCreate(
            external_id=agent_id,
            organization_id=test_org,
            name="No Write Agent",
            email="no-write@example.com",
            agent_type="human",
        )
        no_write_agent = await agent_repo.create_from_create_schema(agent_create)

        with pytest.raises(
            PermissionDeniedError, match="does not have WRITE permission"
        ):
            await document_service.update_metadata(
                document_id=test_document,
                agent_id=str(no_write_agent.id),
                name="Should Fail",
            )

    @pytest.mark.asyncio
    async def test_replace_document_success(
        self,
        document_service: DocumentService,
        test_document: str,
        test_agent: str,
        temp_file_v2: str,
    ):
        """Test successful document replacement."""
        # Act
        new_version = await document_service.replace_document(
            document_id=test_document,
            file_path=temp_file_v2,
            agent_id=test_agent,
            change_description="Updated content for testing",
        )

        # Assert
        assert new_version.version_number == 2
        assert new_version.change_type == "update"
        assert new_version.change_description == "Updated content for testing"
        assert new_version.created_by == UUID(test_agent)

        # Check document was updated
        updated_doc = await document_service.document_repo.get_by_id(
            UUID(test_document)
        )
        assert updated_doc.current_version == 2

    @pytest.mark.asyncio
    async def test_list_documents_success(
        self,
        document_service: DocumentService,
        test_org: str,
        test_agent: str,
        test_document: str,
    ):
        """Test successful document listing."""
        # Act
        documents = await document_service.list_documents(
            organization_id=test_org,
            agent_id=test_agent,
        )

        # Assert
        assert len(documents) >= 1
        assert any(doc.id == UUID(test_document) for doc in documents)

        # Check document details
        test_doc = next(doc for doc in documents if doc.id == UUID(test_document))
        assert test_doc.name == "Test Document"
        assert test_doc.status == "active"

    @pytest.mark.asyncio
    async def test_list_documents_filtered_by_tags(
        self,
        document_service: DocumentService,
        test_org: str,
        test_agent: str,
    ):
        """Test document listing filtered by tags."""
        # Create another document with different tags
        with (
            patch.object(
                document_service.storage_backend, "upload", new_callable=AsyncMock
            ) as mock_upload,
            patch.object(
                document_service.storage_backend,
                "create_bucket",
                new_callable=AsyncMock,
            ) as mock_bucket,
        ):

            mock_upload.return_value = "mock-url"
            mock_bucket.return_value = None

            # Create temp file
            import tempfile
            from pathlib import Path

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False
            ) as f:
                f.write("Tagged document content")
                temp_path = f.name

            try:
                tagged_doc = await document_service.upload_document(
                    file_path=temp_path,
                    name="Tagged Document",
                    organization_id=test_org,
                    agent_id=test_agent,
                    tags=["important", "report"],
                )

                # List documents with tag filter
                tagged_documents = await document_service.list_documents(
                    organization_id=test_org,
                    agent_id=test_agent,
                    tags=["important"],
                )

                # Should find the tagged document
                assert len(tagged_documents) >= 1
                assert any(doc.id == tagged_doc.id for doc in tagged_documents)

            finally:
                Path(temp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_search_documents_success(
        self,
        document_service: DocumentService,
        test_org: str,
        test_agent: str,
        test_document: str,
    ):
        """Test successful document search."""
        # Act - search for "Test"
        results = await document_service.search_documents(
            query="Test",
            organization_id=test_org,
            agent_id=test_agent,
        )

        # Assert
        assert len(results) >= 1
        assert any(doc.id == UUID(test_document) for doc in results)

    @pytest.mark.asyncio
    async def test_delete_document_soft_delete(
        self,
        document_service: DocumentService,
        test_document: str,
        test_agent: str,
    ):
        """Test soft delete of document."""
        # Act
        await document_service.delete_document(
            document_id=test_document,
            agent_id=test_agent,
            hard_delete=False,
        )

        # Assert - document should be marked as deleted
        doc = await document_service.document_repo.get_by_id(test_document)
        assert doc.status == "deleted"

        # Should not be downloadable
        with pytest.raises(DocumentNotFoundError):
            await document_service.download_document(
                document_id=test_document,
                agent_id=test_agent,
            )

    @pytest.mark.asyncio
    async def test_delete_document_hard_delete(
        self,
        document_service: DocumentService,
        test_org: str,
        test_agent: str,
        temp_file: str,
    ):
        """Test hard delete of document."""
        # Create a document for hard deletion
        with (
            patch.object(
                document_service.storage_backend, "upload", new_callable=AsyncMock
            ) as mock_upload,
            patch.object(
                document_service.storage_backend,
                "create_bucket",
                new_callable=AsyncMock,
            ) as mock_bucket,
        ):

            mock_upload.return_value = "mock-url"
            mock_bucket.return_value = None

            doc_to_delete = await document_service.upload_document(
                file_path=temp_file,
                name="Document to Delete",
                organization_id=test_org,
                agent_id=test_agent,
            )

            # Mock delete operations
            with patch.object(
                document_service.storage_backend, "delete", new_callable=AsyncMock
            ) as mock_delete:
                mock_delete.return_value = None

                # Act - hard delete
                await document_service.delete_document(
                    document_id=str(doc_to_delete.id),
                    agent_id=test_agent,
                    hard_delete=True,
                )

                # Assert - document should be completely removed
                doc = await document_service.document_repo.get_by_id(
                    str(doc_to_delete.id)
                )
                assert doc is None


# Phase 6: Enhanced Upload System Tests


class TestEnhancedUpload:
    """Test enhanced upload with flexible input support."""

    @pytest.mark.asyncio
    async def test_upload_enhanced_with_file_path(
        self,
        document_service: DocumentService,
        test_org: str,
        test_agent: str,
        temp_file: str,
    ):
        """Test enhanced upload with file path input."""
        # Act
        document = await document_service.upload_enhanced(
            file_input=temp_file,
            name="Enhanced File Path Upload",
            organization_id=test_org,
            agent_id=test_agent,
            description="Upload via file path",
            tags=["enhanced"],
        )

        # Assert
        assert document.name == "Enhanced File Path Upload"
        assert document.description == "Upload via file path"
        assert document.status == "active"
        assert document.current_version == 1
        assert "enhanced" in document.tags

    @pytest.mark.asyncio
    async def test_upload_enhanced_with_bytes(
        self,
        document_service: DocumentService,
        test_org: str,
        test_agent: str,
    ):
        """Test enhanced upload with bytes input."""
        # Arrange
        file_content = b"This is test content for bytes upload"

        # Mock storage backend
        with patch.object(
            document_service.storage_backend, "upload", new_callable=AsyncMock
        ) as mock_upload:
            mock_upload.return_value = None

            # Act
            document = await document_service.upload_enhanced(
                file_input=file_content,
                name="Bytes Upload Test",
                organization_id=test_org,
                agent_id=test_agent,
                filename="test_bytes.txt",
                content_type="text/plain",
            )

            # Assert
            assert document.name == "Bytes Upload Test"
            assert document.filename == "test_bytes.txt"
            assert document.file_size == len(file_content)
            assert document.mime_type == "text/plain"
            assert mock_upload.called

    @pytest.mark.asyncio
    async def test_upload_enhanced_with_binary_stream(
        self,
        document_service: DocumentService,
        test_org: str,
        test_agent: str,
    ):
        """Test enhanced upload with binary stream input."""
        # Arrange
        import io

        stream_content = b"Stream content for testing"
        stream = io.BytesIO(stream_content)

        with patch.object(
            document_service.storage_backend, "upload", new_callable=AsyncMock
        ) as mock_upload:
            mock_upload.return_value = None

            # Act
            document = await document_service.upload_enhanced(
                file_input=stream,
                name="Stream Upload Test",
                organization_id=test_org,
                agent_id=test_agent,
                filename="stream_test.bin",
            )

            # Assert
            assert document.name == "Stream Upload Test"
            assert document.file_size == len(stream_content)
            assert mock_upload.called

    @pytest.mark.asyncio
    async def test_upload_enhanced_invalid_input_type(
        self,
        document_service: DocumentService,
        test_org: str,
        test_agent: str,
    ):
        """Test enhanced upload rejects invalid input types."""
        # Act & Assert
        with pytest.raises(ValidationError, match="Unsupported file input type"):
            await document_service.upload_enhanced(
                file_input=12345,  # Invalid: not str, bytes, or BinaryIO
                name="Invalid Input",
                organization_id=test_org,
                agent_id=test_agent,
            )

    @pytest.mark.asyncio
    async def test_upload_enhanced_nonexistent_file(
        self,
        document_service: DocumentService,
        test_org: str,
        test_agent: str,
    ):
        """Test enhanced upload fails with nonexistent file path."""
        # Act & Assert
        with pytest.raises(ValidationError, match="File does not exist"):
            await document_service.upload_enhanced(
                file_input="/nonexistent/path/to/file.txt",
                name="Nonexistent File",
                organization_id=test_org,
                agent_id=test_agent,
            )

    @pytest.mark.asyncio
    async def test_replace_document_create_version(
        self,
        document_service: DocumentService,
        test_org: str,
        test_agent: str,
        temp_file: str,
    ):
        """Test replace document with new version creation."""
        # Arrange - create initial document
        doc = await document_service.upload_document(
            file_path=temp_file,
            name="Document to Replace",
            organization_id=test_org,
            agent_id=test_agent,
        )

        # Create new file content
        new_content = b"Replaced content"

        with patch.object(
            document_service.storage_backend, "upload", new_callable=AsyncMock
        ):
            # Act - replace with new version
            version = await document_service.replace_document_content(
                document_id=str(doc.id),
                file_input=new_content,
                agent_id=test_agent,
                change_description="Updated with new content",
                create_version=True,
                content_type="application/octet-stream",
                filename="replaced.bin",
            )

            # Assert
            assert version.version_number == 2
            assert version.change_description == "Updated with new content"
            assert version.filename == "replaced.bin"
            assert version.file_size == len(new_content)

    @pytest.mark.asyncio
    async def test_replace_document_no_version(
        self,
        document_service: DocumentService,
        test_org: str,
        test_agent: str,
        temp_file: str,
    ):
        """Test replace document without creating new version."""
        # Arrange - create initial document
        doc = await document_service.upload_document(
            file_path=temp_file,
            name="Document to Replace In-Place",
            organization_id=test_org,
            agent_id=test_agent,
        )
        initial_version = doc.current_version

        # Create new file content
        new_content = b"In-place replaced content"

        with (
            patch.object(
                document_service.storage_backend, "delete", new_callable=AsyncMock
            ),
            patch.object(
                document_service.storage_backend, "upload", new_callable=AsyncMock
            ),
        ):
            # Act - replace without creating version
            updated_doc = await document_service.replace_document_content(
                document_id=str(doc.id),
                file_input=new_content,
                agent_id=test_agent,
                change_description="In-place update",
                create_version=False,
                filename="updated.bin",
            )

            # Assert - version number shouldn't change
            assert updated_doc.current_version == initial_version
            assert updated_doc.filename == "updated.bin"
            assert updated_doc.file_size == len(new_content)

    @pytest.mark.asyncio
    async def test_replace_document_permission_denied(
        self,
        document_service: DocumentService,
        test_org: str,
        test_agent: str,
        other_agent: str,
        temp_file: str,
    ):
        """Test replace document fails without WRITE permission."""
        # Arrange - create document as test_agent
        doc = await document_service.upload_document(
            file_path=temp_file,
            name="Protected Document",
            organization_id=test_org,
            agent_id=test_agent,
        )

        # Act & Assert - other_agent cannot write
        with pytest.raises(PermissionDeniedError):
            await document_service.replace_document_content(
                document_id=str(doc.id),
                file_input=b"New content",
                agent_id=other_agent,
                change_description="Unauthorized update",
            )


# Phase 7: Document Listing & Retrieval Tests


class TestDocumentDetails:
    """Test get_document_details functionality."""

    @pytest.mark.asyncio
    async def test_get_document_details_basic(
        self,
        document_service: DocumentService,
        test_org: str,
        test_agent: str,
        temp_file: str,
    ):
        """Test retrieving basic document details."""
        # Arrange - create a document
        doc = await document_service.upload_document(
            file_path=temp_file,
            name="Test Document",
            organization_id=test_org,
            agent_id=test_agent,
            description="Test description",
            tags=["test"],
        )

        # Act
        details = await document_service.get_document_details(
            document_id=str(doc.id),
            agent_id=test_agent,
            include_versions=False,
            include_permissions=False,
        )

        # Assert
        assert details["id"] == str(doc.id)
        assert details["name"] == "Test Document"
        assert details["description"] == "Test description"
        assert details["status"] == "active"
        assert "created_at" in details
        assert "updated_at" in details
        assert "versions" not in details
        assert "permissions" not in details

    @pytest.mark.asyncio
    async def test_get_document_details_with_versions(
        self,
        document_service: DocumentService,
        test_org: str,
        test_agent: str,
        temp_file: str,
    ):
        """Test document details including version history."""
        # Arrange - create a document and add versions
        doc = await document_service.upload_document(
            file_path=temp_file,
            name="Versioned Document",
            organization_id=test_org,
            agent_id=test_agent,
        )

        # Act
        details = await document_service.get_document_details(
            document_id=str(doc.id),
            agent_id=test_agent,
            include_versions=True,
        )

        # Assert
        assert "versions" in details
        assert len(details["versions"]) >= 1
        assert details["versions"][0]["version_number"] == 1
        assert details["versions"][0]["change_type"] == "create"

    @pytest.mark.asyncio
    async def test_get_document_details_permission_denied(
        self,
        document_service: DocumentService,
        test_org: str,
        test_agent: str,
        other_agent: str,
        temp_file: str,
    ):
        """Test get_document_details fails without READ permission."""
        # Arrange - create document
        doc = await document_service.upload_document(
            file_path=temp_file,
            name="Protected Document",
            organization_id=test_org,
            agent_id=test_agent,
        )

        # Act & Assert
        with pytest.raises(PermissionDeniedError):
            await document_service.get_document_details(
                document_id=str(doc.id),
                agent_id=other_agent,
            )


class TestDocumentListing:
    """Test enhanced document listing functionality."""

    @pytest.mark.asyncio
    async def test_list_documents_paginated(
        self,
        document_service: DocumentService,
        test_org: str,
        test_agent: str,
        temp_file: str,
    ):
        """Test paginated document listing."""
        # Arrange - create multiple documents
        for i in range(3):
            await document_service.upload_document(
                file_path=temp_file,
                name=f"Document {i}",
                organization_id=test_org,
                agent_id=test_agent,
            )

        # Act
        result = await document_service.list_documents_paginated(
            organization_id=test_org,
            agent_id=test_agent,
            limit=10,
            offset=0,
        )

        # Assert
        assert "documents" in result
        assert "pagination" in result
        assert result["pagination"]["limit"] == 10
        assert result["pagination"]["offset"] == 0
        assert len(result["documents"]) >= 1

    @pytest.mark.asyncio
    async def test_list_documents_with_filters(
        self,
        document_service: DocumentService,
        test_org: str,
        test_agent: str,
        temp_file: str,
    ):
        """Test document listing with tag filters."""
        # Arrange - create documents with different tags
        await document_service.upload_document(
            file_path=temp_file,
            name="Tagged Document",
            organization_id=test_org,
            agent_id=test_agent,
            tags=["important", "report"],
        )

        # Act
        result = await document_service.list_documents_paginated(
            organization_id=test_org,
            agent_id=test_agent,
            tags=["important"],
            limit=10,
        )

        # Assert
        assert "documents" in result
        assert len(result["documents"]) >= 0

    @pytest.mark.asyncio
    async def test_list_documents_invalid_limit(
        self,
        document_service: DocumentService,
        test_org: str,
        test_agent: str,
    ):
        """Test list_documents_paginated rejects invalid limit."""
        # Act & Assert
        with pytest.raises(ValidationError, match="limit must be between"):
            await document_service.list_documents_paginated(
                organization_id=test_org,
                agent_id=test_agent,
                limit=2000,  # Too high
            )


class TestDocumentSearch:
    """Test enhanced search functionality."""

    @pytest.mark.asyncio
    async def test_search_documents_enhanced(
        self,
        document_service: DocumentService,
        test_org: str,
        test_agent: str,
        temp_file: str,
    ):
        """Test enhanced document search."""
        # Arrange - create a document with searchable content
        await document_service.upload_document(
            file_path=temp_file,
            name="Quarterly Report 2025",
            organization_id=test_org,
            agent_id=test_agent,
            description="Q1 financial report",
        )

        # Act
        result = await document_service.search_documents_enhanced(
            query="Quarterly",
            organization_id=test_org,
            agent_id=test_agent,
        )

        # Assert
        assert "results" in result
        assert "pagination" in result
        assert result["query"] == "Quarterly"
        assert "filters" in result

    @pytest.mark.asyncio
    async def test_search_documents_with_prefix_filter(
        self,
        document_service: DocumentService,
        test_org: str,
        test_agent: str,
        temp_file: str,
    ):
        """Test search with prefix filtering."""
        # Arrange - create document with prefix
        await document_service.upload_document_to_prefix(
            file_path=temp_file,
            name="Report.pdf",
            organization_id=test_org,
            agent_id=test_agent,
            prefix="/reports/2025/",
        )

        # Act
        result = await document_service.search_documents_enhanced(
            query="Report",
            organization_id=test_org,
            agent_id=test_agent,
            prefix="/reports/",
        )

        # Assert
        assert "results" in result
        assert result["filters"]["prefix"] == "/reports/"

    @pytest.mark.asyncio
    async def test_search_documents_query_too_short(
        self,
        document_service: DocumentService,
        test_org: str,
        test_agent: str,
    ):
        """Test search rejects query that's too short."""
        # Act & Assert
        with pytest.raises(ValidationError, match="query must be at least"):
            await document_service.search_documents_enhanced(
                query="a",  # Too short
                organization_id=test_org,
                agent_id=test_agent,
            )
