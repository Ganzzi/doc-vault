# DocVault SDK

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Scalable Python SDK for document management and collaboration across organizations and AI agents.

## Installation

```bash
uv add docvault-sdk
# or
pip install docvault-sdk
```

## Quick Start

```python
import asyncio
from doc_vault import DocVaultSDK

async def main():
    async with DocVaultSDK() as vault:
        document = await vault.upload(
            file_path="./report.pdf",
            name="Q4 Financial Report",
            organization_id="org-123",
            agent_id="agent-456"
        )
        content = await vault.download(
            document_id=document.id,
            agent_id="agent-456"
        )
        print(f"Uploaded document: {document.name}")

asyncio.run(main())
```

See [examples/](./examples/) for access control, versioning, and multi-organization patterns.

## Features

- Document management: upload, download, update, delete
- Role-based access control (READ, WRITE, DELETE, SHARE, ADMIN)
- Full version control with restore capabilities
- Multi-organization isolation
- Full-text search via PostgreSQL
- MinIO/S3 cloud storage integration
- AI agent support for human/AI collaboration
- Async-first design using psqlpy

## API Overview

### Document Operations

```python
# Upload
document = await vault.upload(file_path="./doc.pdf", name="Doc",
    organization_id="org-123", agent_id="agent-456")

# Download
content = await vault.download(document_id=document.id, agent_id="agent-456")

# List
result = await vault.list_docs(organization_id="org-123", agent_id="agent-456", limit=50)

# Search
results = await vault.search(query="report", organization_id="org-123", agent_id="agent-456")
```

### Access Control

```python
from doc_vault.database.schemas.permission import PermissionGrant

await vault.set_permissions(
    document_id=document.id,
    permissions=[
        PermissionGrant(agent_id="agent-789", permission="READ"),
        PermissionGrant(agent_id="agent-012", permission="WRITE"),
    ],
    granted_by="agent-456"
)
```

### Version Management

```python
# Get document details with versions
details = await vault.get_document_details(
    document_id=document.id, agent_id="agent-456", include_versions=True)

# Restore previous version
restored = await vault.restore_version(
    document_id=document.id, version_number=2, agent_id="agent-456",
    change_description="Restored version 2")
```

For full API documentation, see [docs/API.md](./docs/API.md).

## Configuration

DocVault supports three configuration patterns:

1. **Direct Config object** (recommended for PyPI users):
   ```python
   from doc_vault.config import Config
   config = Config(postgres_host="localhost", postgres_port=5432, ...)
   async with DocVaultSDK(config=config) as vault: ...
   ```

2. **Environment variables** (recommended for Docker/K8s):
   ```bash
   export POSTGRES_HOST=localhost
   export MINIO_ENDPOINT=localhost:9000
   # ... see docs/ for full reference
   ```

3. **`.env` file** (local development): Copy `.env.example` to `.env` and fill in values.

## Testing

```bash
uv sync --all-groups --all-extras
uv run pytest -m "unit" -q     # PR gate
uv run pytest -q                # full local
```

## License

MIT
