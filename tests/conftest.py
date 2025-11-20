"""
Test configuration and fixtures for DocVault tests.

This module provides shared fixtures for database testing, including
PostgreSQL connection setup, test data creation, and cleanup.
"""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator
from uuid import uuid4, UUID

import pytest
from dotenv import load_dotenv

from doc_vault.config import Config
from doc_vault.database.postgres_manager import PostgreSQLManager
from doc_vault.database.repositories.acl import ACLRepository
from doc_vault.database.repositories.agent import AgentRepository
from doc_vault.database.repositories.document import DocumentRepository
from doc_vault.database.repositories.organization import OrganizationRepository
from doc_vault.database.repositories.version import VersionRepository
from doc_vault.database.schemas.acl import DocumentACLCreate
from doc_vault.database.schemas.agent import AgentCreate
from doc_vault.database.schemas.organization import OrganizationCreate
from doc_vault.services.access_service import AccessService
from doc_vault.services.document_service import DocumentService
from doc_vault.services.version_service import VersionService
from doc_vault.storage.base import StorageBackend
from doc_vault.storage.s3_client import S3StorageBackend


# Load environment variables
load_dotenv()


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def config() -> Config:
    """Create test configuration."""
    # Use environment variables or defaults for testing
    test_config = Config()
    return test_config


@pytest.fixture(scope="session")
async def db_manager(config: Config) -> AsyncGenerator[PostgreSQLManager, None]:
    """Create database manager for tests."""
    manager = PostgreSQLManager(config)

    # Initialize the pool
    await manager.initialize()

    # Initialize database schema for repository tests
    await initialize_database_schema(manager)

    yield manager

    # Cleanup
    await manager.close()


async def initialize_database_schema(manager: PostgreSQLManager) -> None:
    """Initialize database schema if tables don't exist."""
    try:
        # Check if organizations table exists
        result = await manager.execute(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'organizations')"
        )
        table_exists = result.result()[0][0]

        if not table_exists:
            # Read and execute schema SQL
            schema_path = (
                Path(__file__).parent.parent
                / "src"
                / "doc_vault"
                / "sql"
                / "schema.sql"
            )
            if schema_path.exists():
                with open(schema_path, "r") as f:
                    schema_sql = f.read()

                # Split by semicolon and execute each statement
                statements = [
                    stmt.strip() for stmt in schema_sql.split(";") if stmt.strip()
                ]
                for statement in statements:
                    if statement:
                        await manager.execute(statement)
            else:
                raise FileNotFoundError(f"Schema file not found: {schema_path}")
    except Exception as e:
        # If schema initialization fails, continue - tables might already exist
        pass


@pytest.fixture
async def storage_backend(config: Config) -> StorageBackend:
    """Create storage backend for tests."""
    backend = S3StorageBackend(
        endpoint=config.minio_endpoint,
        access_key=config.minio_access_key,
        secret_key=config.minio_secret_key,
        secure=config.minio_secure,
    )
    return backend


@pytest.fixture
async def document_service(
    db_manager: PostgreSQLManager, storage_backend: StorageBackend, config: Config
) -> DocumentService:
    """Create DocumentService instance for tests."""
    service = DocumentService(
        db_manager=db_manager,
        storage_backend=storage_backend,
        bucket_prefix=config.bucket_prefix,
    )
    return service


@pytest.fixture
async def access_service(db_manager: PostgreSQLManager) -> AccessService:
    """Create AccessService instance for tests."""
    service = AccessService(db_manager=db_manager)
    return service


@pytest.fixture
async def version_service(db_manager: PostgreSQLManager) -> VersionService:
    """Create VersionService instance for tests."""
    service = VersionService(db_manager=db_manager)
    return service


@pytest.fixture
async def test_org(db_manager: PostgreSQLManager) -> str:
    """Create a test organization and return its ID."""
    org_repo = OrganizationRepository(db_manager)

    org_id = uuid4()
    org_create = OrganizationCreate(
        id=org_id,
        metadata={"test": True},
    )

    org = await org_repo.create(org_create)
    return str(org.id)


@pytest.fixture
async def test_agent(db_manager: PostgreSQLManager, test_org: str) -> str:
    """Create a test agent and return its ID."""
    agent_repo = AgentRepository(db_manager)

    agent_id = uuid4()
    agent_create = AgentCreate(
        id=agent_id,
        organization_id=UUID(test_org),
        is_active=True,
        metadata={"test": True},
    )

    agent = await agent_repo.create(agent_create)
    return str(agent.id)


@pytest.fixture
async def other_agent(db_manager: PostgreSQLManager, test_org: str) -> str:
    """Create another test agent for permission testing."""
    agent_repo = AgentRepository(db_manager)

    agent_id = uuid4()
    agent_create = AgentCreate(
        id=agent_id,
        organization_id=UUID(test_org),
        is_active=True,
        metadata={"test": True},
    )

    agent = await agent_repo.create(agent_create)
    return str(agent.id)


@pytest.fixture
async def test_document(
    db_manager: PostgreSQLManager,
    storage_backend: StorageBackend,
    test_org: str,
    test_agent: str,
    config: Config,
) -> str:
    """Create a test document and return its ID."""
    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("This is test content for document upload.")
        temp_file_path = f.name

    try:
        # Create document service
        doc_service = DocumentService(
            db_manager=db_manager,
            storage_backend=storage_backend,
            bucket_prefix=config.bucket_prefix,
        )

        # Upload document
        document = await doc_service.upload_document(
            file_path=temp_file_path,
            name="Test Document",
            organization_id=UUID(test_org),
            agent_id=UUID(test_agent),
            description="Test document for integration tests",
            tags=["test", "integration"],
            metadata={"test": True},
        )

        return str(document.id)
    finally:
        # Clean up temp file
        Path(temp_file_path).unlink(missing_ok=True)


@pytest.fixture
async def temp_file() -> AsyncGenerator[str, None]:
    """Create a temporary file for testing uploads."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("This is test content for file upload operations.")
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
async def temp_file_v2() -> AsyncGenerator[str, None]:
    """Create a second temporary file for testing version replacement."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("This is updated test content for version replacement.")
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)
