"""
Tests for v2.2 smart upload string detection.

Tests the automatic detection of file paths vs. text content in upload operations.
"""

import pytest
import tempfile
from pathlib import Path
from uuid import uuid4

from doc_vault import DocVaultSDK
from doc_vault.exceptions import ValidationError


pytestmark = pytest.mark.asyncio


class TestUploadStringDetection:
    """Tests for smart string detection in upload method."""

    async def test_upload_file_path_existing_file(
        self, vault_sdk, test_org, test_agent
    ):
        """Test uploading via file path (file exists on disk)."""
        # Create a temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("File path content")
            temp_path = f.name

        try:
            # Upload via file path
            doc = await vault_sdk.upload(
                file_input=temp_path,
                name="File Path Upload",
                organization_id=test_org.id,
                agent_id=test_agent.id,
            )

            assert doc.name == "File Path Upload"
            assert doc.file_size > 0

            # Verify content
            content = await vault_sdk.download(
                document_id=doc.id, agent_id=test_agent.id
            )
            assert content.decode() == "File path content"

        finally:
            Path(temp_path).unlink(missing_ok=True)

    async def test_upload_text_content_no_file(self, vault_sdk, test_org, test_agent):
        """Test uploading text content (path doesn't exist)."""
        # String that looks like a path but doesn't exist
        text_content = "/this/path/does/not/exist.txt - This is text content!"

        doc = await vault_sdk.upload(
            file_input=text_content,
            name="Text Content Upload",
            organization_id=test_org.id,
            agent_id=test_agent.id,
        )

        assert doc.name == "Text Content Upload"
        assert doc.file_size == len(text_content.encode("utf-8"))

        # Verify content
        content = await vault_sdk.download(document_id=doc.id, agent_id=test_agent.id)
        assert content.decode() == text_content

    async def test_upload_simple_text_string(self, vault_sdk, test_org, test_agent):
        """Test uploading simple text string."""
        text = "Hello, DocVault! This is direct text upload."

        doc = await vault_sdk.upload(
            file_input=text,
            name="Simple Text",
            organization_id=test_org.id,
            agent_id=test_agent.id,
        )

        assert doc.name == "Simple Text"

        # Verify content
        content = await vault_sdk.download(document_id=doc.id, agent_id=test_agent.id)
        assert content.decode() == text

    async def test_upload_unicode_text(self, vault_sdk, test_org, test_agent):
        """Test uploading Unicode text content."""
        text = "Hello 世界! 🎉 DocVault v2.2"

        doc = await vault_sdk.upload(
            file_input=text,
            name="Unicode Text",
            organization_id=test_org.id,
            agent_id=test_agent.id,
        )

        # Verify content
        content = await vault_sdk.download(document_id=doc.id, agent_id=test_agent.id)
        assert content.decode("utf-8") == text

    async def test_upload_empty_string(self, vault_sdk, test_org, test_agent):
        """Test uploading empty string."""
        text = ""

        doc = await vault_sdk.upload(
            file_input=text,
            name="Empty Text",
            organization_id=test_org.id,
            agent_id=test_agent.id,
        )

        assert doc.file_size == 0

        # Verify empty content
        content = await vault_sdk.download(document_id=doc.id, agent_id=test_agent.id)
        assert content == b""

    async def test_upload_large_text_content(self, vault_sdk, test_org, test_agent):
        """Test uploading large text content."""
        # Generate 10KB of text
        text = "x" * 10240

        doc = await vault_sdk.upload(
            file_input=text,
            name="Large Text",
            organization_id=test_org.id,
            agent_id=test_agent.id,
        )

        assert doc.file_size == 10240

        # Verify content
        content = await vault_sdk.download(document_id=doc.id, agent_id=test_agent.id)
        assert len(content) == 10240

    async def test_upload_bytes_still_works(self, vault_sdk, test_org, test_agent):
        """Test that bytes upload still works as before."""
        content_bytes = b"Byte content"

        doc = await vault_sdk.upload(
            file_input=content_bytes,
            name="Bytes Upload",
            organization_id=test_org.id,
            agent_id=test_agent.id,
        )

        assert doc.name == "Bytes Upload"

        # Verify content
        content = await vault_sdk.download(document_id=doc.id, agent_id=test_agent.id)
        assert content == content_bytes

    async def test_upload_binary_io_still_works(self, vault_sdk, test_org, test_agent):
        """Test that BinaryIO upload still works as before."""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".bin", delete=False) as f:
            f.write(b"Binary IO content")
            temp_path = f.name

        try:
            # Upload via BinaryIO
            with open(temp_path, "rb") as file_obj:
                doc = await vault_sdk.upload(
                    file_input=file_obj,
                    name="BinaryIO Upload",
                    organization_id=test_org.id,
                    agent_id=test_agent.id,
                )

            assert doc.name == "BinaryIO Upload"

            # Verify content
            content = await vault_sdk.download(
                document_id=doc.id, agent_id=test_agent.id
            )
            assert content == b"Binary IO content"

        finally:
            Path(temp_path).unlink(missing_ok=True)

    async def test_upload_multiline_text(self, vault_sdk, test_org, test_agent):
        """Test uploading multiline text content."""
        text = """Line 1: Introduction
Line 2: Content
Line 3: Conclusion"""

        doc = await vault_sdk.upload(
            file_input=text,
            name="Multiline Text",
            organization_id=test_org.id,
            agent_id=test_agent.id,
        )

        # Verify content
        content = await vault_sdk.download(document_id=doc.id, agent_id=test_agent.id)
        assert content.decode() == text

    async def test_upload_json_text(self, vault_sdk, test_org, test_agent):
        """Test uploading JSON as text."""
        json_text = '{"key": "value", "number": 123}'

        doc = await vault_sdk.upload(
            file_input=json_text,
            name="JSON Text",
            organization_id=test_org.id,
            agent_id=test_agent.id,
        )

        # Verify content
        content = await vault_sdk.download(document_id=doc.id, agent_id=test_agent.id)
        assert content.decode() == json_text

    async def test_upload_text_with_special_chars(
        self, vault_sdk, test_org, test_agent
    ):
        """Test text with special characters."""
        text = "Special chars: @#$%^&*()_+-={}[]|\\:;\"'<>,.?/"

        doc = await vault_sdk.upload(
            file_input=text,
            name="Special Chars",
            organization_id=test_org.id,
            agent_id=test_agent.id,
        )

        # Verify content
        content = await vault_sdk.download(document_id=doc.id, agent_id=test_agent.id)
        assert content.decode() == text

    async def test_upload_relative_path_as_text(self, vault_sdk, test_org, test_agent):
        """Test that relative paths (non-existent) are treated as text."""
        # Relative path that doesn't exist
        relative_path = "data/documents/report.pdf"

        doc = await vault_sdk.upload(
            file_input=relative_path,
            name="Relative Path Text",
            organization_id=test_org.id,
            agent_id=test_agent.id,
        )

        # Should be treated as text content
        content = await vault_sdk.download(document_id=doc.id, agent_id=test_agent.id)
        assert content.decode() == relative_path

    async def test_upload_absolute_path_nonexistent_as_text(
        self, vault_sdk, test_org, test_agent
    ):
        """Test that non-existent absolute paths are treated as text."""
        # Absolute path that doesn't exist
        abs_path = "/absolutely/does/not/exist/file.txt"

        doc = await vault_sdk.upload(
            file_input=abs_path,
            name="Absolute Path Text",
            organization_id=test_org.id,
            agent_id=test_agent.id,
        )

        # Should be treated as text content
        content = await vault_sdk.download(document_id=doc.id, agent_id=test_agent.id)
        assert content.decode() == abs_path

    async def test_upload_windows_path_as_text(self, vault_sdk, test_org, test_agent):
        """Test Windows-style path (non-existent) as text."""
        win_path = "C:\\Users\\Test\\Documents\\file.txt"

        doc = await vault_sdk.upload(
            file_input=win_path,
            name="Windows Path Text",
            organization_id=test_org.id,
            agent_id=test_agent.id,
        )

        # Should be treated as text content
        content = await vault_sdk.download(document_id=doc.id, agent_id=test_agent.id)
        assert content.decode() == win_path


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
