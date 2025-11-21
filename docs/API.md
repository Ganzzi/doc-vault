# DocVault SDK v2.2 API Reference

Complete API reference for DocVault SDK v2.2.

**What's New in v2.2:**
- 🎯 **100% Type Safety**: All methods return explicit Pydantic models instead of `Dict[str, Any]`
- 📦 **Response Models**: `DocumentListResponse`, `SearchResponse`, `DocumentDetails`, `PermissionListResponse`, `OwnershipTransferResponse`
- 🧠 **Smart Upload Detection**: Automatic detection of file paths vs. text content in uploads
- 🔒 **Model-Only Permissions**: `set_permissions()` now requires `List[PermissionGrant]` (no dicts)
- 🧹 **Cleaner API**: Removed legacy v1.x compatibility helpers
- ✨ **Better IDE Support**: Full autocomplete on all response fields
- See [MIGRATION_v2.1_to_v2.2.md](./MIGRATION_v2.1_to_v2.2.md) for migration guide

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
- [Response Models (v2.2)](#response-models-v22)
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

## Response Models (v2.2)

Starting in v2.2, all SDK methods return explicit Pydantic models instead of generic dictionaries. This provides:
- ✅ **Type Safety**: IDE autocomplete and type checking
- ✅ **Validation**: Automatic field validation
- ✅ **Documentation**: Self-documenting response structures
- ✅ **Compatibility**: Convert to dict with `.model_dump()` if needed

### PaginationMeta

Pagination metadata included in list/search responses.

```python
from doc_vault.database.schemas import PaginationMeta

class PaginationMeta(BaseModel):
    total: int          # Total number of items
    limit: int          # Items per page
    offset: int         # Starting offset
    has_more: bool      # Whether more items exist
```

### DocumentListResponse

Response model for `list_docs()` method.

```python
from doc_vault.database.schemas import DocumentListResponse

class DocumentListResponse(BaseModel):
    documents: List[Document]           # List of documents
    pagination: PaginationMeta          # Pagination information
    filters: Dict[str, Any]             # Applied filters
```

**Example:**
```python
result = await vault.list_docs(org_id=org, agent_id=agent, limit=10)

# Type-safe attribute access
for doc in result.documents:
    print(doc.name)

print(f"Total: {result.pagination.total}")
print(f"Has more: {result.pagination.has_more}")

# Convert to dict if needed
result_dict = result.model_dump()
```

### SearchResponse

Response model for `search()` method.

```python
from doc_vault.database.schemas import SearchResponse

class SearchResponse(BaseModel):
    documents: List[Document]           # Matching documents
    query: str                          # Search query
    pagination: PaginationMeta          # Pagination information
    filters: Dict[str, Any]             # Applied filters
```

**Example:**
```python
result = await vault.search(query="report", org_id=org, agent_id=agent)

print(f"Query: {result.query}")
print(f"Found {result.pagination.total} results")

for doc in result.documents:
    print(f"- {doc.name}")
```

### DocumentDetails

Response model for `get_document_details()` method.

```python
from doc_vault.database.schemas import DocumentDetails

class DocumentDetails(BaseModel):
    document: Document                      # Document metadata
    versions: Optional[List[DocumentVersion]] = None  # Version history (if requested)
    permissions: Optional[List[DocumentACL]] = None   # Permissions (if ADMIN and requested)
    version_count: int                      # Total number of versions
    current_version: int                    # Current version number
```

**Example:**
```python
details = await vault.get_document_details(
    document_id=doc_id,
    agent_id=agent_id,
    include_versions=True
)

print(f"Document: {details.document.name}")
print(f"Current version: {details.current_version}")
print(f"Total versions: {details.version_count}")

if details.versions:
    for v in details.versions:
        print(f"  v{v.version_number}: {v.change_description}")
```

### PermissionListResponse

Response model for `get_permissions()` method.

```python
from doc_vault.database.schemas import PermissionListResponse

class PermissionListResponse(BaseModel):
    document_id: UUID                   # Document UUID
    permissions: List[DocumentACL]      # List of permissions
    total: int                          # Total permission count
    requested_by: Optional[UUID] = None # Agent who requested
    requested_at: datetime              # When retrieved
```

**Example:**
```python
perms = await vault.get_permissions(document_id=doc_id)

print(f"Document has {perms.total} permissions")
print(f"Requested by: {perms.requested_by}")

for acl in perms.permissions:
    print(f"{acl.agent_id}: {acl.permission}")
```

### OwnershipTransferResponse

Response model for `transfer_ownership()` method.

```python
from doc_vault.database.schemas import OwnershipTransferResponse

class OwnershipTransferResponse(BaseModel):
    document: Document                  # Updated document
    old_owner: UUID                     # Previous owner agent ID
    new_owner: UUID                     # New owner agent ID
    transferred_by: UUID                # Agent who performed transfer
    transferred_at: datetime            # Transfer timestamp
    new_permissions: List[DocumentACL]  # Updated permission list
```

**Example:**
```python
result = await vault.transfer_ownership(
    document_id=doc_id,
    new_owner_id=new_owner,
    agent_id=current_owner
)

print(f"Ownership transferred from {result.old_owner} to {result.new_owner}")
print(f"Transferred at: {result.transferred_at}")
print(f"New permissions count: {len(result.new_permissions)}")
```

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

**v2.2 Enhancements:**
- **Smart string detection:** Automatically detects file paths vs. text content
- **Direct text upload:** No temp files needed for text content

**v2.0 Enhancements:**
- **Multiple input types:** file paths (str), bytes, binary streams (BinaryIO)
- **Hierarchical organization:** `prefix` parameter for organizing documents
- **Replace option:** `replace_existing` to update document without creating version

**Parameters:**
- `file_path` (str | bytes | BinaryIO): Document content
  - `str` (file path): If path exists on disk → reads file content
  - `str` (text content): If path doesn't exist → treats as text content ⭐ NEW in v2.2
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
# ⭐ NEW in v2.2: Upload text content directly (no temp file needed!)
doc = await vault.upload(
    file_path="This is my document content",  # Text content
    name="Quick Note",
    organization_id=org_id,
    agent_id=agent_id
)

# Upload from file path (works if file exists)
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

**Smart String Detection (v2.2):**
- If `file_path` is a string and the path exists on disk → reads the file
- If `file_path` is a string and the path doesn't exist → treats as text content
- Text content is automatically encoded to UTF-8 and gets default filename "document.txt"
- For explicit control, use `bytes` or `BinaryIO` types

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

### list_docs() ⭐ UPDATED (v2.2)

List documents with enhanced filtering and pagination.

```python
async def list_docs(
    organization_id: UUID | str,
    agent_id: UUID | str,
    prefix: Optional[str] = None,  # ⭐ NEW in v2.0
    recursive: bool = False,  # ⭐ NEW in v2.0
    max_depth: Optional[int] = None,  # ⭐ NEW in v2.0
    status: Optional[str] = None,
    tags: Optional[List[str]] = None,
    sort_by: str = "created_at",  # ⭐ NEW in v2.0
    sort_order: str = "desc",  # ⭐ NEW in v2.0
    limit: int = 50,
    offset: int = 0,
) -> DocumentListResponse  # ⭐ CHANGED in v2.2: was List[Document]
```

**v2.2 Changes:**
- 🎯 **Type-Safe Response**: Returns `DocumentListResponse` model instead of `Dict[str, Any]`
- ✨ **Better IDE Support**: Full autocomplete on response fields
- 📊 **Rich Metadata**: Includes pagination info and applied filters

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

**Returns:** `DocumentListResponse` - Type-safe response with documents and metadata

**Examples:**
```python
# ⭐ v2.2: Type-safe response with full metadata
result = await vault.list_docs(
    organization_id=org_id,
    agent_id=agent_id,
    limit=10
)

# Access documents via model attributes
for doc in result.documents:
    print(doc.name)

# Access pagination metadata
print(f"Total documents: {result.pagination.total}")
print(f"Has more: {result.pagination.has_more}")
print(f"Showing {result.pagination.limit} of {result.pagination.total}")

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

# Convert to dict if needed (v2.1 compatibility)
result_dict = result.model_dump()
docs_list = result_dict["documents"]
```

---

### search() ⭐ UPDATED (v2.2)

Search documents by text query.

```python
async def search(
    query: str,
    organization_id: UUID | str,
    agent_id: UUID | str,
    prefix: Optional[str] = None,  # ⭐ NEW in v2.0
    limit: int = 20,
) -> SearchResponse  # ⭐ CHANGED in v2.2: was List[Document]
```

**v2.2 Changes:**
- 🎯 **Type-Safe Response**: Returns `SearchResponse` model with query info and metadata
- ✨ **Query Tracking**: Response includes the original query string
- 📊 **Pagination Support**: Full pagination metadata included

**v2.0 Enhancement:** Added `prefix` parameter to scope search

**Parameters:**
- `query` (str): Search query
- `organization_id` (UUID | str): Organization UUID
- `agent_id` (UUID | str): Requester UUID
- `prefix` (Optional[str]): Limit search to prefix
- `limit` (int): Max results

**Returns:** `SearchResponse` - Type-safe response with search results and metadata

**Example:**
```python
# ⭐ v2.2: Type-safe search with metadata
result = await vault.search(
    query="financial report",
    organization_id=org_id,
    agent_id=agent_id,
    prefix="/reports/2025",
    limit=10
)

# Access results via model attributes
print(f"Query: {result.query}")
print(f"Found {result.pagination.total} results")

for doc in result.documents:
    print(f"- {doc.name}")

# Check if there are more results
if result.pagination.has_more:
    print("More results available")
```

---

### get_document_details() ⭐ NEW (v2.2 Updated)

Get comprehensive document information including versions and permissions.

```python
async def get_document_details(
    document_id: UUID | str,
    agent_id: UUID | str,
    include_versions: bool = True,
    include_permissions: bool = False,  # 🔒 v2.1: Requires ADMIN permission
) -> DocumentDetails  # ⭐ CHANGED in v2.2: was Dict[str, Any]
```

**v2.2 Changes:**
- 🎯 **Type-Safe Response**: Returns `DocumentDetails` model with explicit fields
- ✨ **Version Metadata**: Includes `version_count` and `current_version` fields
- 📊 **Optional Fields**: Properly typed optional `versions` and `permissions`

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

**Returns:** `DocumentDetails` - Type-safe response with:
- `document`: Document metadata (Document model)
- `versions`: Optional list of versions (if requested)
- `permissions`: Optional list of permissions (if ADMIN and requested)
- `version_count`: Total number of versions
- `current_version`: Current version number

**Security Notes:**
- Any agent with READ permission can get document details and versions
- **Only ADMIN** permission holders can view permissions (`include_permissions=True`)
- This prevents non-owners from seeing who else has access to the document

**Example:**
```python
# ⭐ v2.2: Type-safe response with rich metadata
details = await vault.get_document_details(
    document_id=doc_id,
    agent_id=agent_id,
    include_versions=True
)

# Access via model attributes
print(f"Document: {details.document.name}")
print(f"Current version: {details.current_version}")
print(f"Total versions: {details.version_count}")

# Type-safe access to versions
if details.versions:
    for v in details.versions:
        print(f"  v{v.version_number}: {v.change_description}")

# Get permissions (only for document owner/ADMIN)
try:
    details_with_perms = await vault.get_document_details(
        document_id=doc_id,
        agent_id=owner_id,  # Must be owner/ADMIN
        include_permissions=True
    )
    # Access permissions via model attribute
    if details_with_perms.permissions:
        print(f"Total permissions: {len(details_with_perms.permissions)}")
        for perm in details_with_perms.permissions:
            print(f"  {perm.agent_id}: {perm.permission}")
except PermissionDeniedError:
    print("Only document owners can view permissions")
```

**Raises:**
- `DocumentNotFoundError`: If document doesn't exist
- `PermissionDeniedError`: If agent lacks READ access
- `PermissionDeniedError`: If `include_permissions=True` and agent doesn't have ADMIN permission

---

## Access Control & Permissions

### get_permissions() ⭐ NEW (v2.2 Updated)

Get permissions for a document.

```python
async def get_permissions(
    document_id: UUID | str,
    agent_id: Optional[UUID | str] = None,
) -> PermissionListResponse  # ⭐ CHANGED in v2.2: was Dict[str, Any]
```

**v2.2 Changes:**
- 🎯 **Type-Safe Response**: Returns `PermissionListResponse` model
- ✨ **Request Metadata**: Includes `requested_by` and `requested_at` fields
- 📊 **Total Count**: Direct access to `total` field

**v2.1 Changes:**
- ❌ Removed unused `org_id` parameter (permissions are document-scoped)
- 🎯 Simplified signature for better API clarity
- 📦 Returns dictionary with metadata instead of plain list

**Replaces:** `get_document_permissions()`, `check_permission()` from v1.x

**Parameters:**
- `document_id` (UUID | str): Document UUID
- `agent_id` (Optional[UUID | str]): Agent UUID to filter permissions for specific agent (None = all permissions)

**Returns:** `PermissionListResponse` - Type-safe response with:
- `document_id`: Document UUID
- `permissions`: List of DocumentACL models
- `total`: Total permission count
- `requested_by`: Agent who requested (if provided)
- `requested_at`: Timestamp of request

**Example:**
```python
# ⭐ v2.2: Type-safe response
perms = await vault.get_permissions(document_id=doc_id)

# Access via model attributes
print(f"Document: {perms.document_id}")
print(f"Total permissions: {perms.total}")
print(f"Requested at: {perms.requested_at}")

for acl in perms.permissions:
    print(f"{acl.agent_id}: {acl.permission}")

# Get permissions for specific agent
agent_perms = await vault.get_permissions(
    document_id=doc_id,
    agent_id=agent_id
)

if agent_perms.permissions:
    print(f"Agent has {agent_perms.total} permissions")
```

**Raises:**
- `DocumentNotFoundError`: If document doesn't exist
- `ValidationError`: If document_id is invalid UUID

---

### set_permissions() ⭐ NEW (v2.2 Updated)

Set or update permissions for a document in bulk.

```python
async def set_permissions(
    document_id: UUID | str,
    permissions: List[PermissionGrant],  # ⭐ v2.2: Model-only (no dicts)
    granted_by: UUID | str,
) -> List[DocumentACL]
```

**v2.2 Changes:**
- 🔒 **Model-Only**: Now **only** accepts `List[PermissionGrant]` (no dict support)
- ✅ **Type Safety**: Full type checking at compile time
- 💡 **Cleaner API**: Removed dict-to-model conversion logic

**v2.1 Changes:**
- 🎯 **Type Safety**: Now accepts `List[PermissionGrant]` instead of `List[dict]`
- ✅ **Validation**: Automatic field validation through Pydantic
- 💡 **Better IDE Support**: Full autocomplete and type hints
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

# ⭐ v2.2 Required: Using PermissionGrant model (dict no longer supported)
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

# ❌ v2.2: Dict format NO LONGER SUPPORTED
# This will raise a type error:
# await vault.set_permissions(
#     document_id=doc_id,
#     permissions=[{"agent_id": agent_id, "permission": "READ"}],  # ❌ Error!
#     granted_by=admin_id
# )
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
