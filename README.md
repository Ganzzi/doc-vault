# DocVault SDK

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation](https://img.shields.io/badge/docs-latest-blue.svg)](https://docvault.readthedocs.io/)
[![Tests](https://img.shields.io/badge/tests-passing-green.svg)](https://github.com/docvault/doc-vault/actions)

**Scalable Python SDK for document management and collaboration across organizations and AI agents.**

DocVault provides a complete solution for document upload, management, version control, and access control. It supports multi-organization isolation, role-based permissions, and integrates seamlessly with PostgreSQL and MinIO/S3 storage.

> **📢 v2.1.0 Released!** Security and type safety refinements over v2.0. See [CHANGELOG.md](./CHANGELOG.md) and [MIGRATION_v2.0_to_v2.1.md](./docs/MIGRATION_v2.0_to_v2.1.md) for details. Key improvements:
> - Enhanced security: Permission viewing restricted to document owners (ADMIN)
> - Type safety: PermissionGrant Pydantic model for validated permissions
> - API cleanup: Removed unused `org_id` parameters from permission methods
> - Documentation: Comprehensive `Raises` sections for all SDK methods

## ✨ Features

- **📁 Document Management**: Upload, download, update, and delete documents
- **🔒 Access Control**: Role-based permissions (READ, WRITE, DELETE, SHARE, ADMIN)
- **📚 Version Control**: Full document history with restore capabilities
- **🏢 Multi-Organization**: Strong isolation between organizations
- **🔍 Full-Text Search**: PostgreSQL-powered document search
- **☁️ Cloud Storage**: MinIO/S3 integration for binary file storage
- **🤖 AI Agent Support**: Designed for both human and AI agent collaboration
- **⚡ High Performance**: Built with async-first design using psqlpy

## 🚀 Quick Start

### Installation

```bash
# Using uv (recommended)
uv add docvault-sdk

# Or using pip
pip install docvault-sdk
```

### Basic Usage

```python
import asyncio
from doc_vault import DocVaultSDK

async def main():
    # Initialize SDK (loads config from .env)
    async with DocVaultSDK() as vault:
        # Upload a document
        document = await vault.upload(
            file_path="./report.pdf",
            name="Q4 Financial Report",
            organization_id="org-123",
            agent_id="agent-456"
        )

        # Download the document
        content = await vault.download(
            document_id=document.id,
            agent_id="agent-456"
        )

        print(f"Uploaded document: {document.name}")

asyncio.run(main())
```

### Try the Examples

Get started quickly with our comprehensive examples:

```bash
# Clone and setup
git clone https://github.com/docvault/doc-vault.git
cd doc-vault

# Install dependencies
uv sync

# Start services
docker-compose up -d

# Run basic usage example
uv run python examples/basic_usage.py
```

See [Examples](./examples/) for detailed usage patterns including access control, versioning, and multi-organization scenarios.

## 📋 Requirements

- **Python**: 3.10+
- **Database**: PostgreSQL 14+
- **Storage**: MinIO or AWS S3
- **Memory**: 512MB+ RAM
- **Disk**: Depends on document storage needs

## ⚙️ Configuration

DocVault supports three flexible configuration patterns to support different deployment scenarios:

### 1. Direct Python Configuration (Recommended for PyPI Users)

For maximum control in your application, pass a `Config` object directly:

```python
from doc_vault import DocVaultSDK
from doc_vault.config import Config

# Create configuration programmatically
config = Config(
    # PostgreSQL Configuration
    postgres_host="localhost",
    postgres_port=5432,
    postgres_user="postgres",
    postgres_password="your_password",
    postgres_db="doc_vault",
    postgres_ssl="disable",
    
    # MinIO/S3 Configuration
    minio_endpoint="localhost:9000",
    minio_access_key="minioadmin",
    minio_secret_key="minioadmin",
    minio_secure=False,
    
    # DocVault Configuration
    bucket_prefix="doc-vault",
    log_level="INFO"
)

# Use the configuration
async with DocVaultSDK(config=config) as vault:
    document = await vault.upload(
        file_path="./report.pdf",
        name="Report",
        organization_id="org-123",
        agent_id="agent-456"
    )
```

### 2. Environment Variables (Recommended for Docker/Kubernetes)

Set environment variables before running your application:

```bash
# PostgreSQL
export POSTGRES_HOST=postgres
export POSTGRES_PORT=5432
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=password
export POSTGRES_DB=doc_vault
export POSTGRES_SSL=disable

# MinIO/S3
export MINIO_ENDPOINT=minio:9000
export MINIO_ACCESS_KEY=minioadmin
export MINIO_SECRET_KEY=minioadmin
export MINIO_SECURE=false

# DocVault
export BUCKET_PREFIX=doc-vault
export LOG_LEVEL=INFO
```

Then use the SDK without passing a config:

```python
from doc_vault import DocVaultSDK

# Automatically loads from environment variables
async with DocVaultSDK() as vault:
    document = await vault.upload(...)
```

### 3. .env File Configuration (Convenient for Local Development)

Create a `.env` file in your project root (git-ignored):

```bash
# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=doc_vault
POSTGRES_SSL=disable

# MinIO/S3 Configuration
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false

# DocVault Configuration
BUCKET_PREFIX=doc-vault
LOG_LEVEL=INFO
```

Install python-dotenv for local development:

```bash
uv sync --all  # or: pip install doc-vault[dev]
```

Then use the SDK as before (automatically loads `.env` file):

```python
from doc_vault import DocVaultSDK

async with DocVaultSDK() as vault:
    document = await vault.upload(...)
```

### Configuration Priority

DocVault uses this priority order when loading configuration (first match wins):

1. **Explicit Config object** - When you pass `Config(...)` directly
2. **Environment variables** - `POSTGRES_*`, `MINIO_*` variables
3. **.env file** - Loaded automatically if `python-dotenv` is available
4. **Defaults** - Hardcoded defaults in the Config class

### Configuration Reference

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `POSTGRES_HOST` | str | `localhost` | PostgreSQL server hostname |
| `POSTGRES_PORT` | int | `5432` | PostgreSQL server port |
| `POSTGRES_USER` | str | *required* | PostgreSQL username |
| `POSTGRES_PASSWORD` | str | *required* | PostgreSQL password |
| `POSTGRES_DB` | str | *required* | PostgreSQL database name |
| `POSTGRES_SSL` | str | `disable` | SSL mode: `disable`, `prefer`, or `require` |
| `MINIO_ENDPOINT` | str | *required* | MinIO/S3 endpoint (e.g., `localhost:9000`) |
| `MINIO_ACCESS_KEY` | str | *required* | MinIO/S3 access key ID |
| `MINIO_SECRET_KEY` | str | *required* | MinIO/S3 secret access key |
| `MINIO_SECURE` | bool | `false` | Use HTTPS for MinIO/S3 |
| `BUCKET_PREFIX` | str | `doc-vault` | Prefix for S3/MinIO bucket names |
| `LOG_LEVEL` | str | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |

## 🏗️ Architecture

DocVault uses a three-layer architecture:

```
┌─────────────────────────────────────────────────────┐
│                   SDK API Layer                     │
│              (core.py - DocVaultSDK)                │
│  High-level methods: upload(), download(), list()   │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│                  Service Layer                      │
│   DocumentService | AccessService | VersionService  │
│         Business logic orchestration                │
└─────────────────────────────────────────────────────┘
                        ↓
┌───────────────────────────┬─────────────────────────┐
│    Repository Layer       │    Storage Layer        │
│  DocumentRepo             │    S3StorageBackend     │
│  OrganizationRepo         │    (MinIO/S3)           │
│  AgentRepo                │                         │
│  VersionRepo              │                         │
│  ACLRepo                  │                         │
└───────────────────────────┴─────────────────────────┘
                        ↓
┌───────────────────────────┬─────────────────────────┐
│      PostgreSQL           │      MinIO/S3           │
│   (Metadata, ACL)         │   (Binary Files)        │
└───────────────────────────┴─────────────────────────┘
```

## 📖 API Reference

### Document Operations

```python
# Upload document
document = await vault.upload(
    file_path="./document.pdf",
    name="Document Name",
    organization_id="org-123",
    agent_id="agent-456",
    description="Optional description",
    tags=["tag1", "tag2"],
    metadata={"custom": "data"}
)

# Download document
content = await vault.download(
    document_id=document.id,
    agent_id="agent-456",
    version=None  # None for latest, or specific version number
)

# Update metadata
updated = await vault.update_metadata(
    document_id=document.id,
    agent_id="agent-456",
    name="New Name",
    description="Updated description"
)

# Replace content (creates new version)
new_version = await vault.replace(
    document_id=document.id,
    file_path="./updated.pdf",
    agent_id="agent-456",
    change_description="Updated content"
)

# Delete document
await vault.delete(document_id=document.id, agent_id="agent-456")

# List documents
documents = await vault.list_documents(
    organization_id="org-123",
    agent_id="agent-456",
    limit=50
)

# Search documents
results = await vault.search(
    query="financial report",
    organization_id="org-123",
    agent_id="agent-456"
)
```

### Access Control

```python
# Set permissions for document (v2.0 API)
await vault.set_permissions(
    document_id=document.id,
    permissions=[
        {"agent_id": "agent-789", "permission": "READ"},
        {"agent_id": "agent-012", "permission": "WRITE"},
    ],
    granted_by="agent-456"
)

# Get permissions
perms_result = await vault.get_permissions(
    document_id=document.id,
    agent_id="agent-789"
)
perms_list = perms_result.get("permissions", [])
for p in perms_list:
    print(f"Permission: {p['permission']}")
```

### Version Management

```python
# Get document details with versions (v2.0 API)
details = await vault.get_document_details(
    document_id=document.id,
    agent_id="agent-456",
    include_versions=True
)
versions = details.get("versions", [])

# Restore previous version
restored = await vault.restore_version(
    document_id=document.id,
    version_number=2,
    agent_id="agent-456",
    change_description="Restored version 2"
)
```

### Organization & Agent Management

```python
# Register organization
org = await vault.register_organization(
    external_id="org-123",
    name="My Organization"
)

# Register agent
agent = await vault.register_agent(
    external_id="agent-456",
    organization_id="org-123",
    name="John Doe",
    agent_type="human"  # or "ai", "service"
)
```

## 💡 Examples

DocVault includes comprehensive examples demonstrating real-world usage patterns:

### Core Functionality
- **[Basic Usage](./examples/basic_usage.py)** - Complete end-to-end workflow
- **[Access Control](./examples/access_control.py)** - Permission management and sharing
- **[Versioning](./examples/versioning.py)** - Document version control
- **[Multi-Organization](./examples/multi_org.py)** - Cross-organization collaboration

### Running Examples

```bash
# Install in development mode
pip install -e .

# Start required services
docker-compose up -d

# Run any example
python examples/basic_usage.py
```

Each example includes detailed comments explaining the concepts and expected output.

## 🛠️ Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/docvault/doc-vault.git
cd doc-vault

# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov

# Run specific test file
uv run pytest tests/test_config.py
```

### Code Quality

```bash
# Format code
uv run black src/

# Lint code
uv run ruff check src/

# Type checking
uv run mypy src/

# Run all quality checks
uv run pre-commit run --all-files
```

### Database Setup

DocVault requires PostgreSQL for metadata and MinIO for file storage.

#### Quick Setup with Docker Compose

```bash
# Start all services
docker-compose up -d

# Check services are running
docker-compose ps

# View service logs
docker-compose logs postgres
docker-compose logs minio
```

#### Manual Setup

```bash
# PostgreSQL
docker run -d --name postgres -p 5432:5432 \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=doc_vault \
  tensorchord/vchord-suite:pg16-latest

# MinIO
docker run -d --name minio -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ":9001"
```

#### Initialize Database

```bash
# Initialize database schema
uv run python -m doc_vault.database.init_db
```

#### Service Access

- **PostgreSQL**: `localhost:5432`
- **MinIO API**: `localhost:9000`
- **MinIO Console**: `http://localhost:9001` (admin/minioadmin)

## 📚 Documentation

- **[Full API Documentation](https://docvault.readthedocs.io/)** - Complete API reference
- **[Examples](./examples/)** - Usage examples and patterns
- **[Contributing Guide](./CONTRIBUTING.md)** - How to contribute
- **[Development Guide](./DEVELOPMENT.md)** - Local development setup

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](./CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes and add tests
4. Run quality checks: `uv run pre-commit run --all-files`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [psqlpy](https://github.com/psycopg/psycopg) for high-performance PostgreSQL
- Uses [Pydantic](https://pydantic-docs.helpmanual.io/) for data validation
- Powered by [MinIO](https://min.io/) for S3-compatible storage

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/docvault/doc-vault/issues)
- **Discussions**: [GitHub Discussions](https://github.com/docvault/doc-vault/discussions)
- **Documentation**: [Read the Docs](https://docvault.readthedocs.io/)

---

**DocVault** - Making document collaboration simple, secure, and scalable.