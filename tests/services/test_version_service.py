"""
Integration tests for VersionService.

Tests version management functionality including listing versions,
restoring versions, and getting version info.
"""

import pytest
from uuid import uuid4

from doc_vault.exceptions import (
    DocumentNotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from doc_vault.services.version_service import VersionService


class TestVersionService:
    """Integration tests for VersionService."""

    @pytest.mark.asyncio
    async def test_list_versions_success(
        self,
        version_service: VersionService,
        test_document: str,
        test_agent: str,
    ):
        """Test successful version listing."""
        # Act
        versions = await version_service.list_versions(
            document_id=test_document,
            agent_id=test_agent,
        )

        # Assert
        assert len(versions) >= 1
        # Versions should be ordered by version_number DESC
        assert versions[0].version_number >= versions[-1].version_number

        # First version should be v1
        v1_versions = [v for v in versions if v.version_number == 1]
        assert len(v1_versions) == 1
        assert v1_versions[0].change_type == "create"

    @pytest.mark.asyncio
    async def test_list_versions_no_permission(
        self,
        version_service: VersionService,
        db_manager,
        test_org: str,
        test_document: str,
    ):
        """Test version listing without permission."""
        # Create agent without permission
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

        with pytest.raises(
            PermissionDeniedError, match="does not have READ permission"
        ):
            await version_service.list_versions(
                document_id=test_document,
                agent_id=str(no_access.id),
            )

    @pytest.mark.asyncio
    async def test_get_version_info_success(
        self,
        version_service: VersionService,
        test_document: str,
        test_agent: str,
    ):
        """Test successful version info retrieval."""
        # Act
        version_info = await version_service.get_version_info(
            document_id=test_document,
            version_number=1,
            agent_id=test_agent,
        )

        # Assert
        assert version_info.version_number == 1
        assert version_info.document_id == test_document
        assert version_info.change_type == "create"
        assert version_info.created_by == test_agent

    @pytest.mark.asyncio
    async def test_get_version_info_not_found(
        self,
        version_service: VersionService,
        test_document: str,
        test_agent: str,
    ):
        """Test version info for non-existent version."""
        with pytest.raises(ValidationError, match="Version 999 not found"):
            await version_service.get_version_info(
                document_id=test_document,
                version_number=999,
                agent_id=test_agent,
            )

    @pytest.mark.asyncio
    async def test_restore_version_success(
        self,
        version_service: VersionService,
        document_service,
        test_document: str,
        test_agent: str,
        temp_file_v2: str,
    ):
        """Test successful version restoration."""
        # First create a second version by replacing the document
        await document_service.replace_document(
            document_id=test_document,
            file_path=temp_file_v2,
            agent_id=test_agent,
            change_description="Second version for restore test",
        )

        # Now restore back to version 1
        restored_version = await version_service.restore_version(
            document_id=test_document,
            version_number=1,
            agent_id=test_agent,
            change_description="Restoring to original version",
        )

        # Assert
        assert restored_version.version_number == 3  # New version created
        assert restored_version.change_type == "restore"
        assert restored_version.change_description == "Restoring to original version"

        # Check that document now points to version 3
        doc = await document_service.document_repo.get_by_id(test_document)
        assert doc.current_version == 3

    @pytest.mark.asyncio
    async def test_restore_version_no_permission(
        self,
        version_service: VersionService,
        db_manager,
        test_org: str,
        test_document: str,
    ):
        """Test version restoration without permission."""
        # Create agent without WRITE permission
        from doc_vault.database.repositories.agent import AgentRepository
        from doc_vault.database.schemas.agent import AgentCreate

        agent_repo = AgentRepository(db_manager)
        no_write_id = str(uuid4())
        no_write_create = AgentCreate(
            external_id=no_write_id,
            organization_id=test_org,
            name="No Write Agent",
            email="nowrite@example.com",
            agent_type="human",
        )
        no_write = await agent_repo.create_from_create_schema(no_write_create)

        with pytest.raises(
            PermissionDeniedError, match="does not have WRITE permission"
        ):
            await version_service.restore_version(
                document_id=test_document,
                version_number=1,
                agent_id=str(no_write.id),
                change_description="Should fail",
            )

    @pytest.mark.asyncio
    async def test_restore_version_not_found(
        self,
        version_service: VersionService,
        test_document: str,
        test_agent: str,
    ):
        """Test restoring non-existent version."""
        with pytest.raises(ValidationError, match="Version 999 not found"):
            await version_service.restore_version(
                document_id=test_document,
                version_number=999,
                agent_id=test_agent,
                change_description="Should fail",
            )

    @pytest.mark.asyncio
    async def test_multiple_versions_workflow(
        self,
        version_service: VersionService,
        document_service,
        test_document: str,
        test_agent: str,
        temp_file: str,
        temp_file_v2: str,
    ):
        """Test complete version workflow with multiple versions."""
        # Document starts with version 1
        versions = await version_service.list_versions(test_document, test_agent)
        assert len(versions) == 1
        assert versions[0].version_number == 1

        # Create version 2
        await document_service.replace_document(
            document_id=test_document,
            file_path=temp_file_v2,
            agent_id=test_agent,
            change_description="Version 2",
        )

        versions = await version_service.list_versions(test_document, test_agent)
        assert len(versions) == 2
        version_nums = [v.version_number for v in versions]
        assert 1 in version_nums
        assert 2 in version_nums

        # Create version 3
        await document_service.replace_document(
            document_id=test_document,
            file_path=temp_file,
            agent_id=test_agent,
            change_description="Version 3",
        )

        versions = await version_service.list_versions(test_document, test_agent)
        assert len(versions) == 3
        version_nums = [v.version_number for v in versions]
        assert 1 in version_nums
        assert 2 in version_nums
        assert 3 in version_nums

        # Restore to version 1 (creates version 4)
        await version_service.restore_version(
            document_id=test_document,
            version_number=1,
            agent_id=test_agent,
            change_description="Restore to v1",
        )

        versions = await version_service.list_versions(test_document, test_agent)
        assert len(versions) == 4
        version_nums = [v.version_number for v in versions]
        assert 1 in version_nums
        assert 2 in version_nums
        assert 3 in version_nums
        assert 4 in version_nums

        # Check that current document version is 4
        doc = await document_service.document_repo.get_by_id(test_document)
        assert doc.current_version == 4
