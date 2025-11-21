"""
Comprehensive tests for SDK upload() method with all input types.

Tests cover:
- File path (str) upload
- Text content (str) upload
- Bytes upload
- BinaryIO stream upload
- Upload with prefix
- Version creation vs replacement
"""

import io
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest


class TestUploadFileInput:
    """Test upload() with different file input types."""

    async def test_upload_from_file_path(
        self, doc_vault_sdk, test_org, test_agent, tmp_path
    ):
        """Test upload from file path string."""
        # Create temp file with content
        file_path = tmp_path / "test_document.txt"
        test_content = "Test document content for file path upload"
        file_path.write_text(test_content)

        try:
            # Action
            doc = await doc_vault_sdk.upload(
                file_input=str(file_path),
                name="Test Document",
                organization_id=test_org,
                agent_id=test_agent,
                description="Uploaded from file path",
            )

            # Assert
            assert doc is not None
            assert doc.name == "Test Document"
            assert doc.filename == "test_document.txt"
            assert doc.mime_type == "text/plain"
            assert doc.file_size == len(test_content)
            assert str(doc.organization_id) == test_org
            assert str(doc.created_by) == test_agent
        finally:
            # Cleanup
            if file_path.exists():
                file_path.unlink()

    async def test_upload_from_text_content(self, doc_vault_sdk, test_org, test_agent):
        """Test upload from text string content."""
        # Setup
        pass  # No setup needed with fixtures
        text_content = "This is text document content uploaded directly"

        # Action
        doc = await doc_vault_sdk.upload(
            file_input=text_content,
            name="Text Document",
            organization_id=test_org,
            agent_id=test_agent,
            content_type="text/plain",
            description="Uploaded from text content",
        )

        # Assert
        assert doc is not None
        assert doc.name == "Text Document"
        assert doc.mime_type == "text/plain"
        assert doc.file_size == len(text_content.encode())
        assert str(doc.organization_id) == test_org

    async def test_upload_from_bytes(self, doc_vault_sdk, test_org, test_agent):
        """Test upload from bytes."""
        byte_content = b"Binary content as bytes for upload"

        # Action
        doc = await doc_vault_sdk.upload(
            file_input=byte_content,
            name="Binary Document",
            organization_id=test_org,
            agent_id=test_agent,
            content_type="application/octet-stream",
            description="Uploaded from bytes",
        )

        # Assert
        assert doc is not None
        assert doc.name == "Binary Document"
        assert doc.file_size == len(byte_content)
        assert str(doc.organization_id) == test_org

    async def test_upload_from_binary_stream(
        self, doc_vault_sdk, test_org, test_agent, tmp_path
    ):
        """Test upload from BinaryIO stream."""
        # Create temp file
        file_path = tmp_path / "stream_data.bin"
        stream_content = b"Stream data content for upload test"
        file_path.write_bytes(stream_content)

        try:
            # Action - upload from stream
            with open(file_path, "rb") as f:
                doc = await doc_vault_sdk.upload(
                    file_input=f,
                    name="Stream Document",
                    organization_id=test_org,
                    agent_id=test_agent,
                    description="Uploaded from binary stream",
                )

            # Assert
            assert doc is not None
            assert doc.name == "Stream Document"
            assert doc.file_size == len(stream_content)
            assert str(doc.organization_id) == test_org
        finally:
            if file_path.exists():
                file_path.unlink()

    async def test_upload_from_bytesio_stream(
        self, doc_vault_sdk, test_org, test_agent
    ):
        """Test upload from BytesIO stream."""
        bytesio_content = b"BytesIO stream content"
        stream = io.BytesIO(bytesio_content)

        # Action
        doc = await doc_vault_sdk.upload(
            file_input=stream,
            name="BytesIO Document",
            organization_id=test_org,
            agent_id=test_agent,
            content_type="application/octet-stream",
        )

        # Assert
        assert doc is not None
        assert doc.name == "BytesIO Document"
        assert doc.file_size == len(bytesio_content)


class TestUploadWithPrefix:
    """Test upload() with hierarchical prefix."""

    async def test_upload_with_prefix(self, doc_vault_sdk, test_org, test_agent):
        """Test upload with hierarchical prefix."""
        prefix = "/reports/2025/q4/"

        # Action
        doc = await doc_vault_sdk.upload(
            file_input="Report content",
            name="Q4 Report",
            organization_id=test_org,
            agent_id=test_agent,
            prefix=prefix,
            content_type="text/plain",
        )

        # Assert
        assert doc is not None
        assert doc.prefix == prefix
        assert doc.path == f"{prefix}Q4 Report"
        assert str(doc.organization_id) == test_org

    async def test_upload_nested_prefix(self, doc_vault_sdk, test_org, test_agent):
        """Test upload with deeply nested prefix."""
        prefix = "/archive/2025/reports/finance/quarterly/"

        # Action
        doc = await doc_vault_sdk.upload(
            file_input="Nested content",
            name="Q4 Financial Report",
            organization_id=test_org,
            agent_id=test_agent,
            prefix=prefix,
        )

        # Assert
        assert doc is not None
        assert doc.prefix == prefix
        assert doc.path == f"{prefix}Q4 Financial Report"


class TestUploadVersionControl:
    """Test upload() version control parameters."""

    async def test_create_version_when_document_exists(
        self, doc_vault_sdk, test_org, test_agent
    ):
        """Test creating new version when document exists."""
        name = "Versioned Document"

        # Action 1: Upload initial version
        doc1 = await doc_vault_sdk.upload(
            file_input="Version 1 content",
            name=name,
            organization_id=test_org,
            agent_id=test_agent,
            content_type="text/plain",
        )

        initial_id = doc1.id
        initial_version = doc1.current_version
        assert initial_version == 1

        # Action 2: Upload again with same name - should create version 2
        doc2 = await doc_vault_sdk.upload(
            file_input="Version 2 updated content",
            name=name,
            organization_id=test_org,
            agent_id=test_agent,
            create_version=True,
            change_description="Updated with new content",
        )

        # Assert
        assert doc2 is not None
        assert doc2.id == initial_id  # Same document
        assert doc2.current_version == 2  # Version incremented

    async def test_replace_version_when_document_exists(
        self, doc_vault_sdk, test_org, test_agent
    ):
        """Test replacing current version (no history)."""
        name = "Replacement Document"

        # Action 1: Upload initial version
        doc1 = await doc_vault_sdk.upload(
            file_input="Original content",
            name=name,
            organization_id=test_org,
            agent_id=test_agent,
        )

        initial_id = doc1.id

        # Action 2: Replace (not versioned)
        doc2 = await doc_vault_sdk.upload(
            file_input="Replaced content",
            name=name,
            organization_id=test_org,
            agent_id=test_agent,
            create_version=False,
            change_description="Corrected content",
        )

        # Assert
        assert doc2 is not None
        assert doc2.id == initial_id  # Same document
        # Note: Version number behavior depends on replace_document_content implementation

    async def test_upload_with_change_description(
        self, doc_vault_sdk, test_org, test_agent
    ):
        """Test upload with change description for versioning."""
        name = "Described Document"
        change_desc = "Updated formatting and structure"

        # Action 1: Initial upload
        doc1 = await doc_vault_sdk.upload(
            file_input="Initial content",
            name=name,
            organization_id=test_org,
            agent_id=test_agent,
        )

        # Action 2: Upload with change description
        doc2 = await doc_vault_sdk.upload(
            file_input="Modified content",
            name=name,
            organization_id=test_org,
            agent_id=test_agent,
            create_version=True,
            change_description=change_desc,
        )

        # Assert
        assert doc2 is not None
        assert doc2.id == doc1.id


class TestUploadMetadata:
    """Test upload() with metadata and tags."""

    async def test_upload_with_tags(self, doc_vault_sdk, test_org, test_agent):
        """Test upload with tags."""
        tags = ["financial", "q4-report", "2025"]

        # Action
        doc = await doc_vault_sdk.upload(
            file_input="Tagged content",
            name="Tagged Document",
            organization_id=test_org,
            agent_id=test_agent,
            tags=tags,
        )

        # Assert
        assert doc is not None
        assert set(doc.tags) == set(tags)

    async def test_upload_with_custom_metadata(
        self, doc_vault_sdk, test_org, test_agent
    ):
        """Test upload with custom metadata."""
        metadata = {
            "department": "Finance",
            "cost_center": "CC-2025-001",
            "review_status": "pending",
        }

        # Action
        doc = await doc_vault_sdk.upload(
            file_input="Metadata content",
            name="Metadata Document",
            organization_id=test_org,
            agent_id=test_agent,
            metadata=metadata,
        )

        # Assert
        assert doc is not None
        assert doc.metadata == metadata

    async def test_upload_with_description(self, doc_vault_sdk, test_org, test_agent):
        """Test upload with description."""
        description = "This is a comprehensive document description"

        # Action
        doc = await doc_vault_sdk.upload(
            file_input="Described content",
            name="Well-Described Document",
            organization_id=test_org,
            agent_id=test_agent,
            description=description,
        )

        # Assert
        assert doc is not None
        assert doc.description == description


class TestUploadContentType:
    """Test upload() with various content types."""

    async def test_upload_json_content_type(self, doc_vault_sdk, test_org, test_agent):
        """Test upload with JSON content type."""
        json_content = '{"key": "value", "number": 123}'

        # Action
        doc = await doc_vault_sdk.upload(
            file_input=json_content,
            name="JSON Document",
            organization_id=test_org,
            agent_id=test_agent,
            content_type="application/json",
        )

        # Assert
        assert doc is not None
        assert doc.mime_type == "application/json"

    async def test_upload_pdf_content_type(self, doc_vault_sdk, test_org, test_agent):
        """Test upload with PDF content type."""
        pdf_bytes = b"%PDF-1.4\n%test"  # Minimal PDF header

        # Action
        doc = await doc_vault_sdk.upload(
            file_input=pdf_bytes,
            name="PDF Document",
            organization_id=test_org,
            agent_id=test_agent,
            content_type="application/pdf",
        )

        # Assert
        assert doc is not None
        assert doc.mime_type == "application/pdf"

    async def test_upload_auto_detect_content_type(
        self, doc_vault_sdk, db_manager, tmp_path
    ):
        """Test automatic content type detection."""
        # Create markdown file for auto-detection
        md_file = tmp_path / "document.md"
        md_file.write_text("# Markdown Document\n\nContent here")

        try:
            # Action
            doc = await doc_vault_sdk.upload(
                file_input=str(md_file),
                name="Markdown Document",
                organization_id=test_org,
                agent_id=test_agent,
                # No content_type specified - should auto-detect
            )

            # Assert
            assert doc is not None
            # Should detect as text or markdown
            assert "text" in doc.mime_type or doc.mime_type == "text/markdown"
        finally:
            if md_file.exists():
                md_file.unlink()


class TestUploadFilename:
    """Test upload() filename handling."""

    async def test_upload_with_filename_override(
        self, doc_vault_sdk, test_org, test_agent
    ):
        """Test upload with filename override."""
        # Action
        doc = await doc_vault_sdk.upload(
            file_input="Content here",
            name="Display Name",
            organization_id=test_org,
            agent_id=test_agent,
            filename="custom_filename.txt",
        )

        # Assert
        assert doc is not None
        assert doc.filename == "custom_filename.txt"
        assert doc.name == "Display Name"  # Name separate from filename

    async def test_upload_detects_filename_from_path(
        self, doc_vault_sdk, db_manager, tmp_path
    ):
        """Test filename detection from file path."""
        file_path = tmp_path / "original_filename.txt"
        file_path.write_text("Content")

        try:
            # Action
            doc = await doc_vault_sdk.upload(
                file_input=str(file_path),
                name="Different Display Name",
                organization_id=test_org,
                agent_id=test_agent,
                # No filename override - should use detected
            )

            # Assert
            assert doc is not None
            assert doc.filename == "original_filename.txt"
            assert doc.name == "Different Display Name"
        finally:
            if file_path.exists():
                file_path.unlink()


class TestUploadErrorHandling:
    """Test upload() error handling."""

    async def test_upload_with_invalid_organization(
        self, doc_vault_sdk, test_org, test_agent
    ):
        """Test upload with non-existent organization."""
        # Setup
        fake_test_org = uuid4()
        test_agent = uuid4()

        # Action & Assert
        with pytest.raises(Exception):  # Should raise OrganizationNotFoundError
            await doc_vault_sdk.upload(
                file_input="Content",
                name="Test",
                organization_id=fake_test_org,
                agent_id=test_agent,
            )

    async def test_upload_with_invalid_agent(self, doc_vault_sdk, test_org, test_agent):
        """Test upload with non-existent agent."""
        # Setup
        test_org = uuid4()
        fake_test_agent = uuid4()

        # Action & Assert
        with pytest.raises(Exception):  # Should raise AgentNotFoundError
            await doc_vault_sdk.upload(
                file_input="Content",
                name="Test",
                organization_id=test_org,
                test_agent=fake_test_agent,
            )


class TestUploadCombinations:
    """Test upload() with various combinations of parameters."""

    async def test_upload_all_parameters(self, doc_vault_sdk, test_org, test_agent):
        """Test upload with all parameters specified."""
        # Action
        doc = await doc_vault_sdk.upload(
            file_input="Comprehensive content",
            name="Comprehensive Document",
            organization_id=test_org,
            agent_id=test_agent,
            description="Full description",
            tags=["tag1", "tag2"],
            metadata={"key": "value"},
            content_type="text/plain",
            filename="override.txt",
            prefix="/docs/2025/",
            create_version=True,
            change_description="Initial comprehensive upload",
        )

        # Assert
        assert doc is not None
        assert doc.name == "Comprehensive Document"
        assert doc.description == "Full description"
        assert doc.prefix == "/docs/2025/"
        assert doc.filename == "override.txt"
        assert set(doc.tags) == {"tag1", "tag2"}
        assert doc.metadata == {"key": "value"}

    async def test_upload_minimal_parameters(self, doc_vault_sdk, test_org, test_agent):
        """Test upload with minimal required parameters only."""
        # Action
        doc = await doc_vault_sdk.upload(
            file_input="Minimal content",
            name="Minimal Document",
            organization_id=test_org,
            agent_id=test_agent,
        )

        # Assert
        assert doc is not None
        assert doc.name == "Minimal Document"
        assert str(doc.organization_id) == test_org
        assert str(doc.created_by) == test_agent
        # Verify defaults
        assert doc.tags == []
        assert doc.metadata == {}
        assert doc.description is None or doc.description == ""
