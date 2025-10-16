"""
Integration tests for DocumentService.

Tests document upload, download, metadata updates, deletion, and search
functionality with real database operations.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

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
        assert document.organization_id == test_org
        assert document.created_by == test_agent
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
        assert updated_doc.metadata == {"updated": True, "version": 2}

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
        assert new_version.created_by == test_agent

        # Check document was updated
        updated_doc = await document_service.document_repo.get_by_id(test_document)
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
        assert any(doc.id == test_document for doc in documents)

        # Check document details
        test_doc = next(doc for doc in documents if doc.id == test_document)
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
        assert any(doc.id == test_document for doc in results)

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
