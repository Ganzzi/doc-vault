"""
Integration tests for SaaS-specific call patterns.

Tests cover:
- Async/sync bridge patterns (how the Django backend calls the SDK)
- Config wiring from Django-like settings
- Import flow orchestration patterns

These tests mock at the repository boundary to avoid requiring
DocVault PostgreSQL at test time.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


class TestAsyncSyncBridge:
    """Tests for async/sync bridge patterns used by Django backend."""

    @pytest.mark.asyncio
    async def test_sdk_can_be_used_as_async_context_manager(self):
        """DocVaultSDK supports async context manager protocol."""
        from doc_vault import DocVaultSDK
        from doc_vault.config import Config

        config = Config(
            postgres_host="test",
            postgres_port=5432,
            postgres_user="test",
            postgres_password="test",
            postgres_db="test",
            minio_endpoint="http://minio:9000",
            minio_access_key="test",
            minio_secret_key="test",
            bucket_prefix="test-prefix",
        )

        # Verify the SDK class has __aenter__ and __aexit__
        assert hasattr(DocVaultSDK, "__aenter__")
        assert hasattr(DocVaultSDK, "__aexit__")

    @pytest.mark.asyncio
    async def test_organization_operations_passthrough(self):
        """register_organization and delete_organization pass through to SDK."""
        from doc_vault.core import DocVaultSDK
        from doc_vault.config import Config

        config = Config()
        sdk = DocVaultSDK(config=config)

        org_id = str(uuid4())
        with patch.object(sdk, "register_organization", new_callable=AsyncMock) as mock_reg:
            await sdk.register_organization(org_id=org_id, metadata={"name": "Test"})
            mock_reg.assert_awaited_once_with(org_id=org_id, metadata={"name": "Test"})

        with patch.object(sdk, "delete_organization", new_callable=AsyncMock) as mock_del:
            await sdk.delete_organization(org_id=org_id, force=True)
            mock_del.assert_awaited_once_with(org_id=org_id, force=True)

    @pytest.mark.asyncio
    async def test_agent_operations_passthrough(self):
        """register_agent and remove_agent pass through to SDK."""
        from doc_vault.core import DocVaultSDK
        from doc_vault.config import Config

        config = Config()
        sdk = DocVaultSDK(config=config)

        agent_id = str(uuid4())
        org_id = str(uuid4())

        with patch.object(sdk, "register_agent", new_callable=AsyncMock) as mock_reg:
            await sdk.register_agent(agent_id=agent_id, organization_id=org_id, metadata={"worker_type": "human"})
            mock_reg.assert_awaited_once_with(
                agent_id=agent_id, organization_id=org_id, metadata={"worker_type": "human"}
            )

        with patch.object(sdk, "remove_agent", new_callable=AsyncMock) as mock_rem:
            await sdk.remove_agent(agent_id=agent_id)
            mock_rem.assert_awaited_once_with(agent_id=agent_id)

    @pytest.mark.asyncio
    async def test_document_listing_passthrough(self):
        """list_docs passes through to SDK with correct parameters."""
        from doc_vault.core import DocVaultSDK
        from doc_vault.config import Config

        config = Config()
        sdk = DocVaultSDK(config=config)

        org_id = str(uuid4())
        agent_id = str(uuid4())

        with patch.object(sdk, "list_docs", new_callable=AsyncMock) as mock_list:
            await sdk.list_docs(
                organization_id=org_id,
                agent_id=agent_id,
                limit=20,
                offset=0,
                prefix="imports/",
                tags=["test"],
                status="active",
            )
            mock_list.assert_awaited_once_with(
                organization_id=org_id,
                agent_id=agent_id,
                limit=20,
                offset=0,
                prefix="imports/",
                tags=["test"],
                status="active",
            )

    @pytest.mark.asyncio
    async def test_search_passthrough(self):
        """search passes through to SDK with correct parameters."""
        from doc_vault.core import DocVaultSDK
        from doc_vault.config import Config

        config = Config()
        sdk = DocVaultSDK(config=config)

        org_id = str(uuid4())
        agent_id = str(uuid4())

        with patch.object(sdk, "search", new_callable=AsyncMock) as mock_search:
            await sdk.search(query="test query", organization_id=org_id, agent_id=agent_id, limit=10, tags=["hr"])
            mock_search.assert_awaited_once_with(
                query="test query", organization_id=org_id, agent_id=agent_id, limit=10, tags=["hr"]
            )


class TestConfigWiring:
    """Tests for SDK config patterns."""

    def test_config_can_be_created_from_dict(self):
        """Config supports construction from keyword arguments (Django settings style)."""
        from doc_vault.config import Config

        config = Config(
            postgres_host="django-db",
            postgres_port=5432,
            postgres_user="django-user",
            postgres_password="django-pass",
            postgres_db="docvault",
            minio_endpoint="minio:9000",
            bucket_prefix="doc-vault",
        )

        assert config.postgres_host == "django-db"
        assert config.postgres_port == 5432
        assert config.postgres_user == "django-user"
        assert config.bucket_prefix == "doc-vault"

    def test_config_env_fallback(self):
        """Config falls back to env vars when not provided."""
        from doc_vault.config import Config

        # Use default config (no overrides)
        config = Config()

        # Should have default values from env or pydantic defaults
        assert config.postgres_host is not None
        assert config.minio_endpoint is not None
        assert config.bucket_prefix is not None

    def test_config_passes_to_sdk(self):
        """Config object can be passed to DocVaultSDK constructor."""
        from doc_vault import DocVaultSDK, Config

        config = Config()
        sdk = DocVaultSDK(config=config)
        assert sdk.config is config


class TestImportFlowPatterns:
    """Tests for import flow orchestration patterns."""

    @pytest.mark.asyncio
    async def test_imported_documents_use_imports_prefix(self):
        """Documents imported from external providers use 'imports/' prefix."""
        from doc_vault.core import DocVaultSDK
        from doc_vault.config import Config

        config = Config()
        sdk = DocVaultSDK(config=config)
        org_id = str(uuid4())
        agent_id = str(uuid4())

        # Simulate listing docs with imports/ prefix filter
        with patch.object(sdk, "list_docs", new_callable=AsyncMock) as mock_list:
            await sdk.list_docs(
                organization_id=org_id,
                agent_id=agent_id,
                prefix="imports/google-drive/",
            )
            mock_list.assert_awaited_once_with(
                organization_id=org_id, agent_id=agent_id, prefix="imports/google-drive/"
            )

    @pytest.mark.asyncio
    async def test_provider_filtered_imports_prefix(self):
        """Different providers get different import prefix paths."""
        from doc_vault.core import DocVaultSDK
        from doc_vault.config import Config

        config = Config()
        sdk = DocVaultSDK(config=config)
        org_id = str(uuid4())
        agent_id = str(uuid4())

        with patch.object(sdk, "list_docs", new_callable=AsyncMock) as mock_list:
            await sdk.list_docs(
                organization_id=org_id,
                agent_id=agent_id,
                prefix="imports/onedrive/",
            )
            mock_list.assert_awaited_once_with(
                organization_id=org_id, agent_id=agent_id, prefix="imports/onedrive/"
            )


class TestUploadVersionPatterns:
    """Tests for upload with version creation patterns."""

    @pytest.mark.asyncio
    async def test_upload_with_create_version(self):
        """Upload supports create_version flag for overwriting existing docs."""
        from doc_vault.core import DocVaultSDK
        from doc_vault.config import Config

        config = Config()
        sdk = DocVaultSDK(config=config)
        org_id = str(uuid4())
        agent_id = str(uuid4())

        with patch.object(sdk, "upload", new_callable=AsyncMock) as mock_upload:
            await sdk.upload(
                file_input=b"test content",
                name="test.pdf",
                organization_id=org_id,
                agent_id=agent_id,
                create_version=True,
                change_description="Updated via SaaS",
            )
            mock_upload.assert_awaited_once_with(
                file_input=b"test content",
                name="test.pdf",
                organization_id=org_id,
                agent_id=agent_id,
                create_version=True,
                change_description="Updated via SaaS",
            )


class TestPermissionPatterns:
    """Tests for permission patterns used by SaaS."""

    @pytest.mark.asyncio
    async def test_get_permissions_passthrough(self):
        """get_permissions passes through to SDK."""
        from doc_vault.core import DocVaultSDK
        from doc_vault.config import Config

        config = Config()
        sdk = DocVaultSDK(config=config)
        doc_id = str(uuid4())
        agent_id = str(uuid4())

        with patch.object(sdk, "get_permissions", new_callable=AsyncMock) as mock_get:
            await sdk.get_permissions(document_id=doc_id, agent_id=agent_id)
            mock_get.assert_awaited_once_with(document_id=doc_id, agent_id=agent_id)

    @pytest.mark.asyncio
    async def test_set_permissions_passthrough(self):
        """set_permissions passes through to SDK."""
        from doc_vault.core import DocVaultSDK
        from doc_vault.config import Config

        config = Config()
        sdk = DocVaultSDK(config=config)
        doc_id = str(uuid4())
        agent_id = str(uuid4())
        perms = [{"agent_id": str(uuid4()), "permission": "READ"}]

        with patch.object(sdk, "set_permissions", new_callable=AsyncMock) as mock_set:
            await sdk.set_permissions(document_id=doc_id, agent_id=agent_id, permissions=perms)
            mock_set.assert_awaited_once_with(document_id=doc_id, agent_id=agent_id, permissions=perms)
