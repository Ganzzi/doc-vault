"""
End-to-end tests for DocVault SDK.

This module tests the complete DocVaultSDK API through integration tests
that exercise the full stack from SDK interface to database and storage.
"""

import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from doc_vault import DocVaultSDK
from doc_vault.config import Config


class TestDocVaultSDK:
    """End-to-end tests for DocVaultSDK."""

    @pytest.mark.asyncio
    async def test_sdk_initialization(self, config: Config):
        """Test SDK initialization and context manager."""
        async with DocVaultSDK(config=config) as sdk:
            assert sdk._initialized
            assert sdk._db_manager is not None
            assert sdk._storage_backend is not None
            assert sdk._document_service is not None
            assert sdk._access_service is not None
            assert sdk._version_service is not None

        # After context exit, should be cleaned up
        assert not sdk._initialized
        assert sdk._db_manager is None
        assert sdk._storage_backend is None
        assert sdk._document_service is None
        assert sdk._access_service is None
        assert sdk._version_service is None

    @pytest.mark.asyncio
    async def test_organization_agent_registration(self, config: Config):
        """Test organization and agent registration."""
        org_external_id = str(uuid4())
        agent_external_id = str(uuid4())

        async with DocVaultSDK(config=config) as sdk:
            # Register organization
            org = await sdk.register_organization(
                external_id=org_external_id,
                name="Test Organization",  # v1.x compat, ignored in v2.0
                metadata={"test": True},
            )
            # In v2.0, external_id becomes the org.id
            assert str(org.id) == org_external_id
            assert org.metadata == {"test": True}

            # Register agent
            agent = await sdk.register_agent(
                external_id=agent_external_id,
                organization_id=org_external_id,
                name="Test Agent",  # v1.x compat, ignored in v2.0
                email="test@example.com",  # v1.x compat, ignored in v2.0
                agent_type="human",  # v1.x compat, ignored in v2.0
                metadata={"test": True},
            )
            # In v2.0, external_id becomes the agent.id
            assert str(agent.id) == agent_external_id
            assert str(agent.organization_id) == org_external_id
            assert agent.metadata == {"test": True}

            # Get organization
            retrieved_org = await sdk.get_organization(org_external_id)
            assert retrieved_org.id == org.id

            # Get agent
            retrieved_agent = await sdk.get_agent(agent_external_id)
            assert retrieved_agent.id == agent.id

    @pytest.mark.asyncio
    async def test_document_lifecycle(self, config: Config, temp_file: str):
        """Test complete document lifecycle: upload, download, update, delete."""
        org_external_id = str(uuid4())
        agent_external_id = str(uuid4())

        async with DocVaultSDK(config=config) as sdk:
            # Register org and agent
            await sdk.register_organization(
                external_id=org_external_id, name="Test Organization"
            )
            await sdk.register_agent(
                external_id=agent_external_id,
                organization_id=org_external_id,
                name="Test Agent",
            )

            # Upload document
            document = await sdk.upload(
                file_input=temp_file,
                name="Test Document",
                organization_id=org_external_id,
                agent_id=agent_external_id,
                description="Test document",
                tags=["test"],
                metadata={"test": True},
            )
            assert document.name == "Test Document"
            assert document.description == "Test document"
            assert document.tags == ["test"]

            # Download document
            content = await sdk.download(
                document_id=document.id, agent_id=agent_external_id
            )
            assert b"This is test content" in content

            # Update metadata
            updated_doc = await sdk.update_metadata(
                document_id=document.id,
                agent_id=agent_external_id,
                name="Updated Test Document",
                description="Updated description",
                tags=["test", "updated"],
                metadata={"test": True, "updated": True},
            )
            assert updated_doc.name == "Updated Test Document"
            assert updated_doc.description == "Updated description"
            assert updated_doc.tags == ["test", "updated"]

            # List documents (v2.0 returns dict with 'documents' key)
            result = await sdk.list_docs(
                organization_id=org_external_id, agent_id=agent_external_id
            )
            documents = result.get("documents", [])
            assert len(documents) >= 1
            # documents are dicts in v2.0
            assert any(str(d.get("id")) == str(document.id) for d in documents)

            # Search documents
            search_response = await sdk.search(
                query="test document",
                organization_id=org_external_id,
                agent_id=agent_external_id,
            )
            search_results = search_response.get("results", [])
            assert len(search_results) >= 1
            assert any(str(d.get("id")) == str(document.id) for d in search_results)

            # Delete document (soft delete)
            await sdk.delete(
                document_id=document.id, agent_id=agent_external_id, hard_delete=False
            )

            # Document should be marked as deleted
            result_after = await sdk.list_docs(
                organization_id=org_external_id,
                agent_id=agent_external_id,
                status="active",
            )
            documents_after = result_after.get("documents", [])
            assert not any(
                str(d.get("id")) == str(document.id) for d in documents_after
            )

    @pytest.mark.asyncio
    async def test_document_versioning(
        self, config: Config, temp_file: str, temp_file_v2: str
    ):
        """Test document versioning: upload, replace, restore."""
        org_external_id = str(uuid4())
        agent_external_id = str(uuid4())

        async with DocVaultSDK(config=config) as sdk:
            # Register org and agent
            await sdk.register_organization(
                external_id=org_external_id, name="Test Organization"
            )
            await sdk.register_agent(
                external_id=agent_external_id,
                organization_id=org_external_id,
                name="Test Agent",
            )

            # Upload initial document
            document = await sdk.upload(
                file_input=temp_file,
                name="Version Test Document",
                organization_id=org_external_id,
                agent_id=agent_external_id,
            )
            assert document.current_version == 1

            # Replace document (creates version 2)
            new_version = await sdk.replace(
                document_id=document.id,
                file_input=temp_file_v2,
                agent_id=agent_external_id,
                change_description="Updated content",
            )
            assert new_version.version_number == 2

            # Check document now points to version 2
            result = await sdk.list_docs(
                organization_id=org_external_id, agent_id=agent_external_id
            )
            updated_doc = result.get("documents", [])
            doc = next(d for d in updated_doc if str(d.get("id")) == str(document.id))
            assert doc.get("current_version") == 2

            # Get all versions
            doc_details = await sdk.get_document_details(
                document_id=document.id,
                agent_id=agent_external_id,
                include_versions=True,
            )
            versions = doc_details.get("versions", [])
            assert len(versions) == 2
            assert versions[0].get("version_number") == 1
            assert versions[1].get("version_number") == 2

            # Download specific version
            old_content = await sdk.download(
                document_id=document.id, agent_id=agent_external_id, version=1
            )
            assert b"This is test content" in old_content

            # Restore version 1 (creates version 3)
            restored = await sdk.restore_version(
                document_id=document.id,
                version_number=1,
                agent_id=agent_external_id,
                change_description="Restored version 1",
            )
            assert restored.version_number == 3
            assert restored.change_type == "restore"

    @pytest.mark.asyncio
    async def test_access_control(self, config: Config, temp_file: str):
        """Test access control: share, revoke, check permissions."""
        org_external_id = str(uuid4())
        owner_external_id = str(uuid4())
        user_external_id = str(uuid4())

        async with DocVaultSDK(config=config) as sdk:
            # Register org and agents
            await sdk.register_organization(
                external_id=org_external_id, name="Test Organization"
            )
            await sdk.register_agent(
                external_id=owner_external_id,
                organization_id=org_external_id,
                name="Owner Agent",
            )
            await sdk.register_agent(
                external_id=user_external_id,
                organization_id=org_external_id,
                name="User Agent",
            )

            # Upload document as owner
            document = await sdk.upload(
                file_input=temp_file,
                name="Access Control Test",
                organization_id=org_external_id,
                agent_id=owner_external_id,
            )

            # Initially, user should not have access
            perms_response = await sdk.get_permissions(
                document_id=document.id, agent_id=owner_external_id
            )
            user_perm = next(
                (
                    p
                    for p in perms_response.get("permissions", [])
                    if str(p.get("agent_id")) == str(user_external_id)
                ),
                None,
            )
            assert user_perm is None  # User not in permissions list

            # Share document with user
            await sdk.set_permissions(
                document_id=document.id,
                granted_by=owner_external_id,
                permissions=[{"agent_id": str(user_external_id), "permission": "READ"}],
            )

            # Now user should have read access
            perms_response = await sdk.get_permissions(
                document_id=document.id  # Don't filter by agent_id to see ALL permissions
            )
            user_perm = next(
                (
                    p
                    for p in perms_response.get("permissions", [])
                    if str(p.get("agent_id")) == str(user_external_id)
                ),
                None,
            )
            assert user_perm is not None
            assert user_perm.get("permission") == "READ"

            # User should be able to see document in accessible list
            result = await sdk.list_docs(
                agent_id=user_external_id, organization_id=org_external_id
            )
            accessible_docs = result.get("documents", [])
            assert any(str(d.get("id")) == str(document.id) for d in accessible_docs)

            # User should be able to download
            content = await sdk.download(
                document_id=document.id, agent_id=user_external_id
            )
            assert b"This is test content" in content

            # Get document permissions
            perms_response = await sdk.get_permissions(
                document_id=document.id  # Get all permissions
            )
            permissions = perms_response.get("permissions", [])
            assert len(permissions) >= 2  # Owner and user

            # Revoke access by explicitly removing the user's permission
            await sdk.set_permissions(
                document_id=document.id,
                granted_by=owner_external_id,
                permissions=[
                    {
                        "agent_id": str(user_external_id),
                        "permission": "READ",
                        "action": "remove",
                    }
                ],
            )

            # User should no longer have access
            perms_response = await sdk.get_permissions(
                document_id=document.id  # Get all permissions
            )
            user_perm = next(
                (
                    p
                    for p in perms_response.get("permissions", [])
                    if str(p.get("agent_id")) == str(user_external_id)
                ),
                None,
            )
            assert user_perm is None  # User removed from permissions

    @pytest.mark.asyncio
    async def test_error_handling(self, config: Config):
        """Test error handling for invalid operations."""
        async with DocVaultSDK(config=config) as sdk:
            # Try to access non-existent organization
            with pytest.raises(Exception):  # Should raise OrganizationNotFoundError
                await sdk.get_organization("non-existent-org")

            # Try to access non-existent agent
            with pytest.raises(Exception):  # Should raise AgentNotFoundError
                await sdk.get_agent("non-existent-agent")

            # Try to download non-existent document
            fake_doc_id = uuid4()
            with pytest.raises(Exception):  # Should raise DocumentNotFoundError
                await sdk.download(
                    document_id=fake_doc_id, agent_id="non-existent-agent"
                )

    @pytest.mark.asyncio
    async def test_sdk_without_context_manager_raises_error(self, config: Config):
        """Test that SDK methods raise error when not initialized."""
        sdk = DocVaultSDK(config=config)

        with pytest.raises(RuntimeError, match="SDK not initialized"):
            await sdk.upload(
                file_input="/tmp/test.txt",
                name="Test",
                organization_id="org-123",
                agent_id="agent-456",
            )
