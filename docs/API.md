# DocVault SDK API Reference

Complete API reference for the DocVault SDK.

## Table of Contents

- [Initialization](#initialization)
- [Document Operations](#document-operations)
- [Access Control](#access-control)
- [Version Management](#version-management)
- [Organization & Agent Management](#organization--agent-management)
- [Configuration](#configuration)
- [Exceptions](#exceptions)

## Initialization

### DocVaultSDK

The main SDK class that provides all document management functionality.

```python
from doc_vault import DocVaultSDK

# Initialize from environment variables (.env file)
async with DocVaultSDK() as vault:
    # Use vault...
    pass

# Initialize with explicit configuration
from doc_vault.config import Config

config = Config(
    postgres_host="localhost",
    postgres_port=5432,
    postgres_user="postgres",
    postgres_password="password",
    postgres_db="doc_vault",
    minio_endpoint="localhost:9000",
    minio_access_key="minioadmin",
    minio_secret_key="minioadmin"
)

async with DocVaultSDK(config=config) as vault:
    # Use vault...
    pass
```

## Document Operations

### upload()

Upload a document to the system.

```python
async def upload(
    file_path: str,
    name: str,
    organization_id: str,
    agent_id: str,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Document
```

**Parameters:**
- `file_path` (str): Path to the file to upload
- `name` (str): Display name for the document
- `organization_id` (str): Organization external ID
- `agent_id` (str): Agent external ID (uploader)
- `description` (Optional[str]): Optional description
- `tags` (Optional[List[str]]): Optional list of tags
- `metadata` (Optional[Dict[str, Any]]): Optional custom metadata

**Returns:** `Document` - The created document object

**Raises:** `AgentNotFoundError`, `OrganizationNotFoundError`, `FileNotFoundError`

### download()

Download a document.

```python
async def download(
    document_id: UUID,
    agent_id: str,
    version: Optional[int] = None,
) -> bytes
```

**Parameters:**
- `document_id` (UUID): Document UUID
- `agent_id` (str): Agent external ID (requester)
- `version` (Optional[int]): Optional version number (None = current)

**Returns:** `bytes` - The document content

**Raises:** `DocumentNotFoundError`, `PermissionDeniedError`

### update_metadata()

Update document metadata.

```python
async def update_metadata(
    document_id: UUID,
    agent_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Document
```

**Parameters:**
- `document_id` (UUID): Document UUID
- `agent_id` (str): Agent external ID (updater)
- `name` (Optional[str]): New name
- `description` (Optional[str]): New description
- `tags` (Optional[List[str]]): New tags
- `metadata` (Optional[Dict[str, Any]]): New metadata

**Returns:** `Document` - Updated document

**Raises:** `DocumentNotFoundError`, `PermissionDeniedError`

### replace()

Replace document content (creates new version).

```python
async def replace(
    document_id: UUID,
    file_path: str,
    agent_id: str,
    change_description: str,
) -> DocumentVersion
```

**Parameters:**
- `document_id` (UUID): Document UUID
- `file_path` (str): Path to new file content
- `agent_id` (str): Agent external ID (updater)
- `change_description` (str): Description of the change

**Returns:** `DocumentVersion` - The new version

**Raises:** `DocumentNotFoundError`, `PermissionDeniedError`

### delete()

Delete a document.

```python
async def delete(
    document_id: UUID,
    agent_id: str,
    hard_delete: bool = False,
) -> None
```

**Parameters:**
- `document_id` (UUID): Document UUID
- `agent_id` (str): Agent external ID (deleter)
- `hard_delete` (bool): If True, permanently delete; if False, soft delete

**Raises:** `DocumentNotFoundError`, `PermissionDeniedError`

### list_documents()

List documents accessible to an agent.

```python
async def list_documents(
    organization_id: str,
    agent_id: str,
    status: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Document]
```

**Parameters:**
- `organization_id` (str): Organization external ID
- `agent_id` (str): Agent external ID (requester)
- `status` (Optional[str]): Filter by status ('active', 'draft', 'archived', 'deleted')
- `tags` (Optional[List[str]]): Filter by tags
- `limit` (int): Maximum results (default: 50)
- `offset` (int): Pagination offset (default: 0)

**Returns:** `List[Document]` - Accessible documents

### search()

Search documents by text query.

```python
async def search(
    query: str,
    organization_id: str,
    agent_id: str,
    limit: int = 20,
) -> List[Document]
```

**Parameters:**
- `query` (str): Search query
- `organization_id` (str): Organization external ID
- `agent_id` (str): Agent external ID (requester)
- `limit` (int): Maximum results (default: 20)

**Returns:** `List[Document]` - Matching documents

## Access Control

### share()

Share a document with another agent.

```python
async def share(
    document_id: UUID,
    agent_id: str,
    permission: str,
    granted_by: str,
    expires_at=None,
) -> None
```

**Parameters:**
- `document_id` (UUID): Document UUID
- `agent_id` (str): Agent external ID to grant access to
- `permission` (str): Permission level ('READ', 'WRITE', 'DELETE', 'SHARE', 'ADMIN')
- `granted_by` (str): Agent external ID granting access
- `expires_at` (Optional[datetime]): Optional expiration datetime

**Raises:** `DocumentNotFoundError`, `AgentNotFoundError`, `PermissionDeniedError`

### revoke()

Revoke access to a document.

```python
async def revoke(
    document_id: UUID,
    agent_id: str,
    permission: str,
    revoked_by: str,
) -> None
```

**Parameters:**
- `document_id` (UUID): Document UUID
- `agent_id` (str): Agent external ID to revoke access from
- `permission` (str): Permission to revoke
- `revoked_by` (str): Agent external ID revoking access

**Raises:** `DocumentNotFoundError`, `AgentNotFoundError`, `PermissionDeniedError`

### check_permission()

Check if an agent has a specific permission on a document.

```python
async def check_permission(
    document_id: UUID,
    agent_id: str,
    permission: str,
) -> bool
```

**Parameters:**
- `document_id` (UUID): Document UUID
- `agent_id` (str): Agent external ID
- `permission` (str): Permission to check

**Returns:** `bool` - True if agent has permission

### list_accessible_documents()

List documents accessible to an agent.

```python
async def list_accessible_documents(
    agent_id: str,
    organization_id: str,
    permission: Optional[str] = None,
) -> List[Document]
```

**Parameters:**
- `agent_id` (str): Agent external ID
- `organization_id` (str): Organization external ID
- `permission` (Optional[str]): Optional permission filter

**Returns:** `List[Document]` - Accessible documents

### get_document_permissions()

Get all permissions for a document.

```python
async def get_document_permissions(
    document_id: UUID,
    agent_id: str,
) -> List[ACL]
```

**Parameters:**
- `document_id` (UUID): Document UUID
- `agent_id` (str): Agent external ID (must have ADMIN permission)

**Returns:** `List[ACL]` - Document permissions

**Raises:** `DocumentNotFoundError`, `PermissionDeniedError`

## Version Management

### get_versions()

Get all versions of a document.

```python
async def get_versions(
    document_id: UUID,
    agent_id: str,
) -> List[DocumentVersion]
```

**Parameters:**
- `document_id` (UUID): Document UUID
- `agent_id` (str): Agent external ID (requester)

**Returns:** `List[DocumentVersion]` - Document versions

**Raises:** `DocumentNotFoundError`, `PermissionDeniedError`

### restore_version()

Restore a previous version (creates new version).

```python
async def restore_version(
    document_id: UUID,
    version_number: int,
    agent_id: str,
    change_description: str,
) -> DocumentVersion
```

**Parameters:**
- `document_id` (UUID): Document UUID
- `version_number` (int): Version to restore
- `agent_id` (str): Agent external ID (restorer)
- `change_description` (str): Description of the restore

**Returns:** `DocumentVersion` - New version created from restore

**Raises:** `DocumentNotFoundError`, `PermissionDeniedError`

### get_version_info()

Get information about a specific version.

```python
async def get_version_info(
    document_id: UUID,
    version_number: int,
    agent_id: str,
) -> DocumentVersion
```

**Parameters:**
- `document_id` (UUID): Document UUID
- `version_number` (int): Version number
- `agent_id` (str): Agent external ID (requester)

**Returns:** `DocumentVersion` - Version information

**Raises:** `DocumentNotFoundError`, `PermissionDeniedError`

## Organization & Agent Management

### register_organization()

Register a new organization (idempotent).

```python
async def register_organization(
    external_id: str,
    name: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Organization
```

**Parameters:**
- `external_id` (str): External organization ID
- `name` (str): Organization name
- `metadata` (Optional[Dict[str, Any]]): Optional custom metadata

**Returns:** `Organization` - The organization

### register_agent()

Register a new agent (idempotent).

```python
async def register_agent(
    external_id: str,
    organization_id: str,
    name: str,
    email: Optional[str] = None,
    agent_type: str = "human",
    metadata: Optional[Dict[str, Any]] = None,
) -> Agent
```

**Parameters:**
- `external_id` (str): External agent ID
- `organization_id` (str): Organization external ID
- `name` (str): Agent name
- `email` (Optional[str]): Optional email
- `agent_type` (str): 'human', 'ai', or 'service'
- `metadata` (Optional[Dict[str, Any]]): Optional custom metadata

**Returns:** `Agent` - The agent

### get_organization()

Get organization by external ID.

```python
async def get_organization(external_id: str) -> Organization
```

**Parameters:**
- `external_id` (str): Organization external ID

**Returns:** `Organization` - The organization

**Raises:** `OrganizationNotFoundError`

### get_agent()

Get agent by external ID.

```python
async def get_agent(external_id: str) -> Agent
```

**Parameters:**
- `external_id` (str): Agent external ID

**Returns:** `Agent` - The agent

**Raises:** `AgentNotFoundError`

## Configuration

### Config

Configuration class for DocVault SDK.

```python
from doc_vault.config import Config

# Load from environment variables
config = Config.from_env()

# Or create explicitly
config = Config(
    postgres_host="localhost",
    postgres_port=5432,
    postgres_user="postgres",
    postgres_password="password",
    postgres_db="doc_vault",
    postgres_ssl="disable",
    minio_endpoint="localhost:9000",
    minio_access_key="minioadmin",
    minio_secret_key="minioadmin",
    minio_secure=False,
    bucket_prefix="doc-vault",
    log_level="INFO"
)
```

**Environment Variables:**
- `POSTGRES_HOST`: Database host (default: localhost)
- `POSTGRES_PORT`: Database port (default: 5432)
- `POSTGRES_USER`: Database user (required)
- `POSTGRES_PASSWORD`: Database password (required)
- `POSTGRES_DB`: Database name (required)
- `POSTGRES_SSL`: SSL mode (default: disable)
- `MINIO_ENDPOINT`: MinIO endpoint (required)
- `MINIO_ACCESS_KEY`: MinIO access key (required)
- `MINIO_SECRET_KEY`: MinIO secret key (required)
- `MINIO_SECURE`: Use HTTPS (default: false)
- `BUCKET_PREFIX`: S3 bucket prefix (default: doc-vault)
- `LOG_LEVEL`: Logging level (default: INFO)

## Exceptions

DocVault defines custom exceptions for different error conditions:

### AgentNotFoundError
Raised when an agent cannot be found by external ID.

### OrganizationNotFoundError
Raised when an organization cannot be found by external ID.

### DocumentNotFoundError
Raised when a document cannot be found.

### PermissionDeniedError
Raised when an agent doesn't have permission for an operation.

### ValidationError
Raised when input validation fails.

### StorageError
Raised when storage operations fail.

### DatabaseError
Raised when database operations fail.

All exceptions inherit from `DocVaultError` for easy catching:

```python
from doc_vault.exceptions import DocVaultError

try:
    # SDK operations...
    pass
except DocVaultError as e:
    # Handle DocVault-specific errors
    print(f"DocVault error: {e}")
```

## Data Models

### Document

```python
class Document:
    id: UUID
    organization_id: UUID
    name: str
    description: Optional[str]
    filename: str
    file_size: int
    mime_type: Optional[str]
    storage_path: str
    current_version: int
    status: str  # 'draft', 'active', 'archived', 'deleted'
    created_by: UUID
    updated_by: Optional[UUID]
    metadata: Dict[str, Any]
    tags: List[str]
    created_at: datetime
    updated_at: datetime
```

### DocumentVersion

```python
class DocumentVersion:
    id: UUID
    document_id: UUID
    version_number: int
    filename: str
    file_size: int
    storage_path: str
    mime_type: Optional[str]
    change_description: Optional[str]
    change_type: str  # 'create', 'update', 'restore'
    created_by: UUID
    created_at: datetime
    metadata: Dict[str, Any]
```

### ACL

```python
class ACL:
    id: UUID
    document_id: UUID
    agent_id: UUID
    permission: str  # 'READ', 'WRITE', 'DELETE', 'SHARE', 'ADMIN'
    granted_by: UUID
    granted_at: datetime
    expires_at: Optional[datetime]
```

### Organization

```python
class Organization:
    id: UUID
    external_id: str
    name: str
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
```

### Agent

```python
class Agent:
    id: UUID
    external_id: str
    organization_id: UUID
    name: str
    email: Optional[str]
    agent_type: str  # 'human', 'ai', 'service'
    metadata: Dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime