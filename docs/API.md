# DocVault SDK v2.1 API Reference

Complete API reference for DocVault SDK v2.1.

**What's New in v2.1:**
- 🔒 **Enhanced Security**: Permission viewing restricted to document owners (ADMIN permission)
- 🎯 **Type Safety**: `PermissionGrant` Pydantic model for type-safe permission operations
- 📝 **Improved Documentation**: Comprehensive `Raises` sections in all method docstrings
- 🧹 **API Cleanup**: Removed unused parameters, cleaner method signatures
- ✅ **Better Validation**: Field-level validation for permissions and UUIDs
- See [MIGRATION_v2.0_to_v2.1.md](./MIGRATION_v2.0_to_v2.1.md) for migration guide

**Major Changes from v1.x:**
- UUID-based entity model (organizations & agents use external UUIDs as primary keys)
- Hierarchical document organization with prefix support
- Unified permissions API (`get_permissions` / `set_permissions`)
- Enhanced upload system (file paths, bytes, streams)
- Comprehensive document details retrieval
- See [BREAKING_CHANGES.md](./plan/v2/BREAKING_CHANGES.md) for v1→v2 migration guide

---

## Table of Contents

- [Initialization](#initialization)
- [Organization & Agent Management](#organization--agent-management)
- [Document Operations](#document-operations)
- [Access Control & Permissions](#access-control--permissions)
- [Version Management](#version-management)
- [Configuration](#configuration)
- [Exceptions](#exceptions)

---

## Initialization

### DocVaultSDK

The main SDK class providing all document management functionality.

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
    postgres_ssl="disable",
    minio_endpoint="localhost:9000",
    minio_access_key="minioadmin",
    minio_secret_key="minioadmin",
    minio_secure=False,
    bucket_prefix="doc-vault",
    log_level="INFO"
)

async with DocVaultSDK(config=config) as vault:
    # Use vault...
    pass
```

**Important:** Always use the SDK as an async context manager to ensure proper resource cleanup.

---

## Organization & Agent Management

### register_organization()

Register a new organization using an external UUID.

```python
async def register_organization(
    external_id: str,
    name: str = None,  # Deprecated in v2.0
    metadata: Optional[Dict[str, Any]] = None,
) -> Organization
```

**v2.0 Changes:**
- `external_id` is now used as the primary UUID
- `name` parameter is deprecated (kept for v1.x compatibility but ignored)
- Organizations no longer store name/metadata in their core record

**Parameters:**
- `external_id` (str): **UUID string** - Must be a valid UUID v4
- `name` (Optional[str]): Deprecated, ignored in v2.0
- `metadata` (Optional[Dict]): Custom metadata (stored but not indexed)

**Returns:** `Organization` - The registered organization

**Example:**
```python
import uuid

org_id = str(uuid.uuid4())  # Generate UUID
org = await vault.register_organization(
    external_id=org_id,
    metadata={"industry": "technology"}
)
```

**Raises:** `DatabaseError`, `ValidationError`

---

### register_agent()

Register a new agent (user or AI) within an organization.

```python
async def register_agent(
    external_id: str,
    organization_id: str,
    name: str = None,  # Deprecated in v2.0
    email: str = None,  # Deprecated in v2.0
    agent_type: str = None,  # Deprecated in v2.0
    is_active: bool = True,
    metadata: Optional[Dict[str, Any]] = None,
) -> Agent
```

**v2.0 Changes:**
- `external_id` is now used as the primary UUID
- `name`, `email`, `agent_type` parameters are deprecated
- Agents no longer store identity information

**Parameters:**
- `external_id` (str): **UUID string** - Must be a valid UUID v4
- `organization_id` (str): Organization UUID
- `name`, `email`, `agent_type`: Deprecated, ignored in v2.0
- `is_active` (bool): Whether agent is active (default: True)
- `metadata` (Optional[Dict]): Custom metadata

**Returns:** `Agent` - The registered agent

**Example:**
```python
agent_id = str(uuid.uuid4())
agent = await vault.register_agent(
    external_id=agent_id,
    organization_id=org_id,
    is_active=True,
    metadata={"role": "admin"}
)
```

**Raises:** `OrganizationNotFoundError`, `DatabaseError`

---

### delete_organization() ⭐ NEW

Delete an organization and optionally cascade delete related data.

```python
async def delete_organization(
    org_id: str | UUID,
    force: bool = False
) -> None
```

**Parameters:**
- `org_id` (str | UUID): Organization UUID
- `force` (bool): If True, cascade delete agents and documents; if False, fail if organization has related data

**Example:**
```python
# Safe delete (fails if organization has agents/documents)
await vault.delete_organization(org_id=org_id, force=False)

# Force delete (removes everything)
await vault.delete_organization(org_id=org_id, force=True)
```

**Raises:** `OrganizationNotFoundError`, `DatabaseError`, `ValidationError`

---

### remove_agent() ⭐ NEW

Remove an agent from an organization (soft delete by marking inactive).

```python
async def remove_agent(
    agent_id: str | UUID
) -> None
```

**Parameters:**
- `agent_id` (str | UUID): Agent UUID

**Example:**
```python
await vault.remove_agent(agent_id=agent_id)
```

**Raises:** `AgentNotFoundError`, `DatabaseError`

---

## Document Operations

### upload()

Upload a document with support for multiple input types.

```python
async def upload(
    file_path: Union[str, bytes, BinaryIO],
    name: str,
    organization_id: str | UUID,
    agent_id: str | UUID,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    prefix: Optional[str] = None,  # ⭐ NEW in v2.0
    replace_existing: Optional[UUID] = None,  # ⭐ NEW in v2.0
) -> Document
```

**v2.0 Enhancements:**
- **Multiple input types:** file paths (str), bytes, binary streams (BinaryIO)
- **Hierarchical organization:** `prefix` parameter for organizing documents
- **Replace option:** `replace_existing` to update document without creating version

**Parameters:**
- `file_path` (str | bytes | BinaryIO): Document content
  - `str`: Path to file on disk
  - `bytes`: In-memory document content
  - `BinaryIO`: Binary stream (e.g., `open(file, 'rb')`)
- `name` (str): Display name for the document
- `organization_id` (str | UUID): Organization UUID
- `agent_id` (str | UUID): Uploader UUID
- `description` (Optional[str]): Document description
- `tags` (Optional[List[str]]): Tags for categorization
- `metadata` (Optional[Dict]): Custom metadata
- `prefix` (Optional[str]): Hierarchical prefix (e.g., "/reports/2025/q1")
- `replace_existing` (Optional[UUID]): Replace this document's content without versioning

**Returns:** `Document` - The created/updated document

**Examples:**
```python
# Upload from file path
doc = await vault.upload(
    file_path="/path/to/report.pdf",
    name="Q1 Report",
    organization_id=org_id,
    agent_id=agent_id,
    prefix="/reports/2025/q1"
)

# Upload from bytes
content = b"Document content here"
doc = await vault.upload(
    file_path=content,
    name="In-Memory Document",
    organization_id=org_id,
    agent_id=agent_id
)

# Upload from stream
with open("large_file.pdf", "rb") as f:
    doc = await vault.upload(
        file_path=f,
        name="Streamed Upload",
        organization_id=org_id,
        agent_id=agent_id
    )

# Replace existing document content
doc = await vault.upload(
    file_path="/path/to/updated.pdf",
    name="Updated Report",
    organization_id=org_id,
    agent_id=agent_id,
    replace_existing=existing_doc_id  # Replaces without versioning
)
```

**Raises:** `AgentNotFoundError`, `OrganizationNotFoundError`, `FileNotFoundError`, `PermissionDeniedError`

---

### download()

Download a document.

```python
async def download(
    document_id: UUID | str,
    agent_id: UUID | str,
    version: Optional[int] = None,
) -> bytes
```

**Parameters:**
- `document_id` (UUID | str): Document UUID
- `agent_id` (UUID | str): Requester UUID
- `version` (Optional[int]): Specific version number (None = current)

**Returns:** `bytes` - Document content

**Example:**
```python
# Download current version
content = await vault.download(document_id=doc_id, agent_id=agent_id)

# Download specific version
v1_content = await vault.download(
    document_id=doc_id, 
    agent_id=agent_id, 
    version=1
)
```

**Raises:** `DocumentNotFoundError`, `PermissionDeniedError`

---

### replace()

Replace document content (creates new version).

```python
async def replace(
    document_id: UUID | str,
    file_path: str,
    agent_id: UUID | str,
    change_description: str,
) -> DocumentVersion
```

**Parameters:**
- `document_id` (UUID | str): Document UUID
- `file_path` (str): Path to new content
- `agent_id` (UUID | str): Updater UUID
- `change_description` (str): Description of changes

**Returns:** `DocumentVersion` - The new version

**Example:**
```python
new_version = await vault.replace(
    document_id=doc_id,
    file_path="/path/to/updated.pdf",
    agent_id=agent_id,
    change_description="Updated financial projections"
)
```

**Raises:** `DocumentNotFoundError`, `PermissionDeniedError`

---

### update_metadata()

Update document metadata without changing content.

```python
async def update_metadata(
    document_id: UUID | str,
    agent_id: UUID | str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Document
```

**Parameters:**
- `document_id` (UUID | str): Document UUID
- `agent_id` (UUID | str): Updater UUID
- `name`, `description`, `tags`, `metadata`: Fields to update

**Returns:** `Document` - Updated document

**Example:**
```python
doc = await vault.update_metadata(
    document_id=doc_id,
    agent_id=agent_id,
    tags=["reviewed", "approved"],
    metadata={"approval_date": "2025-11-20"}
)
```

---

### delete()

Delete a document (soft or hard delete).

```python
async def delete(
    document_id: UUID | str,
    agent_id: UUID | str,
    hard_delete: bool = False,
) -> None
```

**Parameters:**
- `document_id` (UUID | str): Document UUID
- `agent_id` (UUID | str): Deleter UUID
- `hard_delete` (bool): True = permanent, False = mark as deleted

**Example:**
```python
# Soft delete (reversible)
await vault.delete(document_id=doc_id, agent_id=agent_id, hard_delete=False)

# Hard delete (permanent)
await vault.delete(document_id=doc_id, agent_id=agent_id, hard_delete=True)
```

---

### list_docs() ⭐ UPDATED

List documents with enhanced filtering and pagination.

```python
async def list_docs(
    organization_id: UUID | str,
    agent_id: UUID | str,
    prefix: Optional[str] = None,  # ⭐ NEW
    recursive: bool = False,  # ⭐ NEW
    max_depth: Optional[int] = None,  # ⭐ NEW
    status: Optional[str] = None,
    tags: Optional[List[str]] = None,
    sort_by: str = "created_at",  # ⭐ NEW
    sort_order: str = "desc",  # ⭐ NEW
    limit: int = 50,
    offset: int = 0,
) -> List[Document]
```

**v2.0 Enhancements:**
- Hierarchical listing with `prefix`, `recursive`, `max_depth`
- Sorting options with `sort_by` and `sort_order`
- Permission-filtered results

**Parameters:**
- `organization_id` (UUID | str): Organization UUID
- `agent_id` (UUID | str): Requester UUID
- `prefix` (Optional[str]): Filter by prefix (e.g., "/reports/2025")
- `recursive` (bool): Include subdirectories
- `max_depth` (Optional[int]): Maximum depth for recursive listing
- `status` (Optional[str]): Filter by status
- `tags` (Optional[List[str]]): Filter by tags
- `sort_by` (str): Sort field (default: "created_at")
- `sort_order` (str): "asc" or "desc" (default: "desc")
- `limit` (int): Max results (default: 50)
- `offset` (int): Pagination offset

**Examples:**
```python
# List all documents
docs = await vault.list_docs(
    organization_id=org_id,
    agent_id=agent_id
)

# List documents in specific folder
reports = await vault.list_docs(
    organization_id=org_id,
    agent_id=agent_id,
    prefix="/reports/2025"
)

# Recursive listing with depth limit
all_docs = await vault.list_docs(
    organization_id=org_id,
    agent_id=agent_id,
    prefix="/reports",
    recursive=True,
    max_depth=3
)

# Filtered and sorted
filtered = await vault.list_docs(
    organization_id=org_id,
    agent_id=agent_id,
    status="active",
    tags=["important"],
    sort_by="name",
    sort_order="asc",
    limit=20
)
```

---

### search()

Search documents by text query.

```python
async def search(
    query: str,
    organization_id: UUID | str,
    agent_id: UUID | str,
    prefix: Optional[str] = None,  # ⭐ NEW
    limit: int = 20,
) -> List[Document]
```

**v2.0 Enhancement:** Added `prefix` parameter to scope search

**Parameters:**
- `query` (str): Search query
- `organization_id` (UUID | str): Organization UUID
- `agent_id` (UUID | str): Requester UUID
- `prefix` (Optional[str]): Limit search to prefix
- `limit` (int): Max results

**Example:**
```python
results = await vault.search(
    query="financial report",
    organization_id=org_id,
    agent_id=agent_id,
    prefix="/reports/2025",
    limit=10
)
```

---

### get_document_details() ⭐ NEW (v2.1 Updated)

Get comprehensive document information including versions and permissions.

```python
async def get_document_details(
    document_id: UUID | str,
    agent_id: UUID | str,
    include_versions: bool = True,
    include_permissions: bool = False,  # 🔒 v2.1: Requires ADMIN permission
) -> Dict[str, Any]
```

**v2.1 Security Enhancement:**
- 🔒 **Permission Viewing Restricted**: Only document owners (ADMIN permission) can view permissions
- ✅ Prevents information leakage about document access
- 🛡️ Non-owners receive `PermissionDeniedError` if `include_permissions=True`

**Replaces:** `get_versions()`, `get_version_info()` from v1.x

**Parameters:**
- `document_id` (UUID | str): Document UUID
- `agent_id` (UUID | str): Requester UUID
- `include_versions` (bool): Include version history (default: True)
- `include_permissions` (bool): Include permission details (default: False)
  - ⚠️ **Requires ADMIN permission** on the document

**Returns:** Dictionary with:
- `document`: Document details (always included)
- `versions`: List of versions (if `include_versions=True`)
- `permissions`: Permission list (if `include_permissions=True` **and** agent has ADMIN)

**Security Notes:**
- Any agent with READ permission can get document details and versions
- **Only ADMIN** permission holders can view permissions (`include_permissions=True`)
- This prevents non-owners from seeing who else has access to the document

**Example:**
```python
# Get document details with versions (any agent with READ access)
details = await vault.get_document_details(
    document_id=doc_id,
    agent_id=agent_id,
    include_versions=True,
    include_permissions=False  # Safe for non-owners
)

print(f"Document: {details['document']['name']}")
print(f"Current version: {details['document']['current_version']}")
print(f"Total versions: {len(details.get('versions', []))}")

for version in details.get('versions', []):
    print(f"  v{version['version_number']}: {version['change_description']}")

# Get permissions (only for document owner/ADMIN)
try:
    details_with_perms = await vault.get_document_details(
        document_id=doc_id,
        agent_id=owner_id,  # Must be owner/ADMIN
        include_permissions=True
    )
    print(f"Permissions: {details_with_perms['permissions']}")
except PermissionDeniedError:
    print("Only document owners can view permissions")
```

**Raises:**
- `DocumentNotFoundError`: If document doesn't exist
- `PermissionDeniedError`: If agent lacks READ access
- `PermissionDeniedError`: If `include_permissions=True` and agent doesn't have ADMIN permission

---

## Access Control & Permissions

### get_permissions() ⭐ NEW (v2.1 Updated)

Get permissions for a document.

```python
async def get_permissions(
    document_id: UUID | str,
    agent_id: Optional[UUID | str] = None,
) -> Dict[str, Any]
```

**v2.1 Changes:**
- ❌ Removed unused `org_id` parameter (permissions are document-scoped)
- 🎯 Simplified signature for better API clarity
- 📦 Returns dictionary with metadata instead of plain list

**Replaces:** `get_document_permissions()`, `check_permission()` from v1.x

**Parameters:**
- `document_id` (UUID | str): Document UUID
- `agent_id` (Optional[UUID | str]): Agent UUID to filter permissions for specific agent (None = all permissions)

**Returns:** Dictionary with permissions and metadata:
```python
{
    "document_id": str,
    "permissions": [
        {
            "agent_id": str,
            "permission": str,
            "granted_by": str,
            "granted_at": datetime,
            "expires_at": Optional[datetime],
            "metadata": Optional[Dict]
        },
        ...
    ],
    "count": int
}
```

**Example:**
```python
# Get all permissions for a document
perms = await vault.get_permissions(
    document_id=doc_id
)

print(f"Total permissions: {perms['count']}")
for perm in perms['permissions']:
    print(f"{perm['agent_id']}: {perm['permission']}")

# Get permissions for specific agent
agent_perms = await vault.get_permissions(
    document_id=doc_id,
    agent_id=agent_id
)

if agent_perms['permissions']:
    print(f"Agent has {len(agent_perms['permissions'])} permissions")
```

**Raises:**
- `DocumentNotFoundError`: If document doesn't exist
- `ValidationError`: If document_id is invalid UUID

---

### set_permissions() ⭐ NEW (v2.1 Updated)

Set or update permissions for a document in bulk.

```python
async def set_permissions(
    document_id: UUID | str,
    permissions: List[PermissionGrant],  # 🎯 v2.1: Now uses typed model
    granted_by: UUID | str,
) -> List[DocumentACL]
```

**v2.1 Changes:**
- 🎯 **Type Safety**: Now accepts `List[PermissionGrant]` instead of `List[dict]`
- ✅ **Validation**: Automatic field validation through Pydantic
- 💡 **Better IDE Support**: Full autocomplete and type hints
- 🔄 **Backward Compatible**: Still accepts `List[dict]` format
- ❌ Removed unused `org_id` parameter

**Replaces:** `share()`, `revoke()` from v1.x

**Parameters:**
- `document_id` (UUID | str): Document UUID
- `permissions` (List[PermissionGrant]): List of permission grants (see model below)
- `granted_by` (UUID | str): Granter UUID (must have ADMIN or SHARE permission)

**Returns:** List[DocumentACL] - Created/updated permission records

**PermissionGrant Model (v2.1):**
```python
from doc_vault.database.schemas.permission import PermissionGrant

class PermissionGrant(BaseModel):
    """Type-safe permission grant model."""
    agent_id: UUID | str          # Agent receiving permission
    permission: str               # READ, WRITE, DELETE, SHARE, ADMIN
    expires_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
```

**Validation Rules:**
- `permission` must be one of: READ, WRITE, DELETE, SHARE, ADMIN
- `agent_id` must be valid UUID string or UUID object
- Automatic field validation prevents runtime errors

**Examples:**
```python
from doc_vault.database.schemas.permission import PermissionGrant

# 🎯 v2.1 Recommended: Using PermissionGrant model
await vault.set_permissions(
    document_id=doc_id,
    permissions=[
        PermissionGrant(
            agent_id=agent_id,
            permission="READ"
        )
    ],
    granted_by=admin_id
)

# 🔄 Backward Compatible: Using dict (still works)
await vault.set_permissions(
    document_id=doc_id,
    permissions=[
        {"agent_id": str(agent_id), "permission": "READ"}
    ],
    granted_by=admin_id
)

# Multiple permissions with typed model
await vault.set_permissions(
    document_id=doc_id,
    permissions=[
        PermissionGrant(agent_id=viewer_id, permission="READ"),
        PermissionGrant(agent_id=editor_id, permission="WRITE"),
        PermissionGrant(agent_id=admin_id, permission="ADMIN"),
    ],
    granted_by=owner_id
)

# With expiration
from datetime import datetime, timedelta

await vault.set_permissions(
    document_id=doc_id,
    permissions=[
        PermissionGrant(
            agent_id=temp_user_id,
            permission="READ",
            expires_at=datetime.now() + timedelta(days=7),
            metadata={"reason": "temporary access for review"}
        )
    ],
    granted_by=admin_id
)
```

**Permission Levels:**
- **READ**: View document content
- **WRITE**: Modify document content/metadata
- **DELETE**: Delete document
- **SHARE**: Grant permissions to others
- **ADMIN**: Full control (inherits all permissions)

**Raises:**
- `DocumentNotFoundError`: If document doesn't exist
- `AgentNotFoundError`: If granting agent doesn't exist
- `PermissionDeniedError`: If granting agent lacks ADMIN/SHARE permission
- `ValidationError`: If permission data is invalid (e.g., invalid permission level)

---

### check_permissions() ⭐ NEW

Check multiple permissions for an agent.

```python
async def check_permissions(
    document_id: UUID | str,
    agent_id: UUID | str,
    permissions: List[str],
) -> Dict[str, bool]
```

**Parameters:**
- `document_id` (UUID | str): Document UUID
- `agent_id` (UUID | str): Agent UUID
- `permissions` (List[str]): Permissions to check

**Returns:** Dictionary mapping permission to boolean

**Example:**
```python
perms = await vault.check_permissions(
    document_id=doc_id,
    agent_id=agent_id,
    permissions=["READ", "WRITE", "DELETE"]
)

if perms["READ"]:
    print("Agent can read")
if perms["WRITE"]:
    print("Agent can write")
```

---

### transfer_ownership() ⭐ NEW

Transfer document ownership to another agent.

```python
async def transfer_ownership(
    document_id: UUID | str,
    new_owner_id: UUID | str,
    transferred_by: UUID | str,
) -> None
```

**Parameters:**
- `document_id` (UUID | str): Document UUID
- `new_owner_id` (UUID | str): New owner UUID
- `transferred_by` (UUID | str): Current owner UUID (must have ADMIN)

**Example:**
```python
await vault.transfer_ownership(
    document_id=doc_id,
    new_owner_id=new_admin_id,
    transferred_by=current_admin_id
)
```

---

## Version Management

Versioning is now handled through `get_document_details()` and `replace()`.

### Get Version History

```python
details = await vault.get_document_details(
    document_id=doc_id,
    agent_id=agent_id,
    include_versions=True
)

versions = details.get("versions", [])
for v in versions:
    print(f"Version {v['version_number']}: {v['change_description']}")
```

### Download Specific Version

```python
# Download version 2
content = await vault.download(
    document_id=doc_id,
    agent_id=agent_id,
    version=2
)
```

### Create New Version

```python
new_version = await vault.replace(
    document_id=doc_id,
    file_path="/path/to/updated.pdf",
    agent_id=agent_id,
    change_description="Updated with Q4 data"
)
```

---

## Configuration

### Config Class

```python
from doc_vault.config import Config

config = Config(
    # PostgreSQL Configuration
    postgres_host: str = "localhost",
    postgres_port: int = 5432,
    postgres_user: str = "postgres",
    postgres_password: str = "password",
    postgres_db: str = "doc_vault",
    postgres_ssl: str = "disable",  # disable, prefer, require
    
    # MinIO/S3 Configuration
    minio_endpoint: str = "localhost:9000",
    minio_access_key: str = "minioadmin",
    minio_secret_key: str = "minioadmin",
    minio_secure: bool = False,
    
    # DocVault Configuration
    bucket_prefix: str = "doc-vault",
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
)
```

### Configuration Sources (Priority Order)

1. **Direct Config object** - Highest priority
2. **Environment variables** - `POSTGRES_*`, `MINIO_*`, etc.
3. **.env file** - If `python-dotenv` is installed
4. **Defaults** - Hardcoded defaults

---

## Exceptions

### Core Exceptions

```python
from doc_vault.exceptions import (
    DocVaultError,           # Base exception
    DatabaseError,           # Database operation failed
    StorageError,            # Storage operation failed
    ValidationError,         # Invalid input
    
    # Entity Not Found
    OrganizationNotFoundError,
    AgentNotFoundError,
    DocumentNotFoundError,
    VersionNotFoundError,
    
    # Permission Errors
    PermissionDeniedError,
    InsufficientPermissionsError,
)
```

### Error Handling Example

```python
from doc_vault.exceptions import DocumentNotFoundError, PermissionDeniedError

try:
    content = await vault.download(document_id=doc_id, agent_id=agent_id)
except DocumentNotFoundError:
    print("Document does not exist")
except PermissionDeniedError:
    print("Agent lacks READ permission")
except Exception as e:
    print(f"Unexpected error: {e}")
```

---

## Migration from v1.x

### API Method Mapping

| v1.x Method | v2.0 Replacement | Notes |
|-------------|------------------|-------|
| `share()` | `set_permissions()` | Bulk API, more flexible |
| `revoke()` | `set_permissions()` | Same method for grant/revoke |
| `check_permission()` | `get_permissions()` or `check_permissions()` | More efficient bulk checking |
| `list_accessible_documents()` | `list_docs()` | Enhanced with prefix support |
| `get_document_permissions()` | `get_permissions()` | Unified API |
| `get_versions()` | `get_document_details(include_versions=True)` | More comprehensive |
| `get_version_info()` | `get_document_details(include_versions=True)` | Returns all versions |

### Code Migration Examples

#### Sharing Documents

```python
# v1.x
await vault.share(
    document_id=doc_id,
    agent_id=viewer_id,
    permission="READ",
    granted_by=owner_id
)

# v2.0
await vault.set_permissions(
    document_id=doc_id,
    org_id=org_id,
    permissions=[{"agent_id": str(viewer_id), "permission": "READ"}],
    granted_by=owner_id
)
```

#### Checking Permissions

```python
# v1.x
has_read = await vault.check_permission(
    document_id=doc_id,
    agent_id=agent_id,
    permission="READ"
)

# v2.0
perms = await vault.check_permissions(
    document_id=doc_id,
    agent_id=agent_id,
    permissions=["READ"]
)
has_read = perms["READ"]
```

#### Getting Version History

```python
# v1.x
versions = await vault.get_versions(
    document_id=doc_id,
    agent_id=agent_id
)

# v2.0
details = await vault.get_document_details(
    document_id=doc_id,
    agent_id=agent_id,
    include_versions=True
)
versions = details.get("versions", [])
```

---

## Best Practices

### 1. UUID Management

```python
import uuid

# Always use UUIDs for entities
org_id = str(uuid.uuid4())
agent_id = str(uuid.uuid4())

# Never use hardcoded strings
# ❌ Bad: org_id = "my-org-001"
# ✅ Good: org_id = str(uuid.uuid4())
```

### 2. Hierarchical Organization

```python
# Use meaningful prefix structures
prefixes = {
    "reports": "/reports/2025/q1",
    "contracts": "/legal/contracts/2025",
    "invoices": "/finance/invoices/november"
}

doc = await vault.upload(
    file_path=path,
    name="Q1 Report",
    organization_id=org_id,
    agent_id=agent_id,
    prefix=prefixes["reports"]
)
```

### 3. Permission Management

```python
# Grant minimal permissions initially
await vault.set_permissions(
    document_id=doc_id,
    org_id=org_id,
    permissions=[
        {"agent_id": str(viewer_id), "permission": "READ"}
    ],
    granted_by=admin_id
)

# Escalate only when needed
await vault.set_permissions(
    document_id=doc_id,
    org_id=org_id,
    permissions=[
        {"agent_id": str(viewer_id), "permission": "WRITE"}
    ],
    granted_by=admin_id
)
```

### 4. Error Handling

```python
from doc_vault.exceptions import (
    DocumentNotFoundError,
    PermissionDeniedError,
    DatabaseError
)

try:
    doc = await vault.download(document_id=doc_id, agent_id=agent_id)
except DocumentNotFoundError:
    # Handle missing document
    logger.error(f"Document {doc_id} not found")
except PermissionDeniedError:
    # Handle permission issue
    logger.warning(f"Agent {agent_id} lacks access")
except DatabaseError as e:
    # Handle database errors
    logger.error(f"Database error: {e}")
    raise
```

---

## Additional Resources

- [BREAKING_CHANGES.md](./plan/v2/BREAKING_CHANGES.md) - Complete migration guide
- [QUICK_REFERENCE.md](./plan/v2/QUICK_REFERENCE.md) - Quick migration cheat sheet
- [Examples](../examples/) - Code examples for common use cases
- [README.md](../README.md) - Project overview and setup

---

**DocVault SDK v2.0** - Scalable document management for organizations and AI agents.
