# DocVault v2.0 Quick Reference

**Version**: 2.0.0  
**Last Updated**: November 20, 2025

---

## 📋 What's New in v2.0

### Core Changes
- 🆔 **UUID-based IDs**: Direct UUID primary keys (no more external_id)
- 🗂️ **Hierarchical Documents**: Organize docs with prefixes like `/reports/2025/q1/`
- 📤 **Flexible Upload**: Support file paths, bytes, and binary streams
- 🔐 **Unified Permissions**: Get/set permissions in bulk operations
- 🗑️ **Entity Deletion**: Delete organizations and remove agents
- 📊 **Enhanced Listing**: Recursive listing with depth control

### Removed
- ❌ `external_id` fields (use UUID `id` directly)
- ❌ `name`, `email`, `agent_type` in entities (store externally)
- ❌ `share()`, `revoke()`, `check_permission()` methods
- ❌ `list_accessible_documents()`, `get_document_permissions()`
- ❌ `get_versions()`, `get_version_info()`

---

## 🚀 Quick Start Migration

### 1. Update Installation
```bash
pip install docvault-sdk==2.0.0
```

### 2. Entity Registration

#### Before (v1.x)
```python
await vault.register_organization(
    external_id="org-123",
    name="Acme Corp"
)
await vault.register_agent(
    external_id="agent-456",
    organization_id="org-123",
    name="John Doe",
    email="john@acme.com"
)
```

#### After (v2.0)
```python
import uuid

org_id = uuid.uuid4()
agent_id = uuid.uuid4()

await vault.register_organization(id=org_id)
await vault.register_agent(id=agent_id, organization_id=org_id)

# Store names externally in your app
your_org_data = {
    org_id: {"name": "Acme Corp", "domain": "acme.com"}
}
your_agent_data = {
    agent_id: {"name": "John Doe", "email": "john@acme.com"}
}
```

### 3. Document Upload

#### Before (v1.x)
```python
doc = await vault.upload(
    file_path="/path/to/file.pdf",
    name="Report",
    organization_id="org-123",
    agent_id="agent-456"
)
```

#### After (v2.0)
```python
# Option 1: File path (same as before, but with UUIDs)
doc = await vault.upload(
    file_path="/path/to/file.pdf",
    file_type="application/pdf",
    name="Report",
    organization_id=org_uuid,
    agent_id=agent_uuid,
    prefix="/reports/2025/"  # NEW: hierarchical organization
)

# Option 2: Bytes (NEW)
doc = await vault.upload(
    file_path=file_bytes,
    file_type="application/pdf",
    name="Report",
    organization_id=org_uuid,
    agent_id=agent_uuid
)

# Option 3: Stream (NEW)
with open("file.pdf", "rb") as f:
    doc = await vault.upload(
        file_path=f,
        file_type="application/pdf",
        name="Report",
        organization_id=org_uuid,
        agent_id=agent_uuid
    )
```

### 4. Permissions

#### Before (v1.x)
```python
# Share document
await vault.share(doc_id, "agent-789", "READ", "agent-456")

# Check permission
has_access = await vault.check_permission(doc_id, "agent-789", "READ")

# Revoke
await vault.revoke(doc_id, "agent-789", "READ", "agent-456")
```

#### After (v2.0)
```python
from doc_vault.database.schemas.acl import Permission

# Get all permissions
permissions = await vault.get_permissions(
    document_id=doc_uuid,
    agent_id=agent_uuid,
    org_id=org_uuid
)

# Set permissions (grant and revoke in one call)
await vault.set_permissions(
    document_id=doc_uuid,
    agent_id=agent_uuid,
    org_id=org_uuid,
    permissions=[
        Permission(agent_id=agent1_uuid, type="READ"),
        Permission(agent_id=agent2_uuid, type="WRITE"),
        Permission(agent_id=agent3_uuid, type="DELETE"),
    ],
    granted_by=granter_uuid
)
```

### 5. Document Listing

#### Before (v1.x)
```python
docs = await vault.list_documents(
    organization_id="org-123",
    agent_id="agent-456",
    status="active"
)
```

#### After (v2.0)
```python
# List all documents
docs = await vault.list_docs(
    org_id=org_uuid,
    agent_id=agent_uuid
)

# List by prefix (hierarchical)
docs = await vault.list_docs(
    org_id=org_uuid,
    agent_id=agent_uuid,
    prefix="/reports/2025/q1/",
    recursive=True,
    max_depth=3
)

# List without permission check
docs = await vault.list_docs(
    org_id=org_uuid,
    agent_id=agent_uuid,
    permission_check=False  # List all, not just accessible
)
```

### 6. Document Details & Versions

#### Before (v1.x)
```python
versions = await vault.get_versions(doc_id, agent_id)
version_info = await vault.get_version_info(doc_id, 2, agent_id)
```

#### After (v2.0)
```python
# Get document with versions and permissions
details = await vault.get_document_details(
    document_id=doc_uuid,
    org_id=org_uuid,
    agent_id=agent_uuid,
    include_versions=True,
    include_permissions=True  # Only if caller is owner
)

# Access the data
print(details.id)
print(details.name)
print(details.versions)  # List of all versions
print(details.permissions)  # List of permissions (if included)
```

### 7. Delete Operations (NEW)

```python
# Delete organization
await vault.delete_organization(org_id=org_uuid)

# Remove agent
await vault.remove_agent(agent_id=agent_uuid)
```

---

## 🔄 API Method Mapping

| v1.x Method | v2.0 Replacement |
|-------------|------------------|
| `register_organization(external_id, name, ...)` | `register_organization(id: UUID)` |
| `register_agent(external_id, org_id, name, email, agent_type, ...)` | `register_agent(id: UUID, organization_id: UUID)` |
| `upload(file_path: str, ...)` | `upload(file_path: Union[str, bytes, BinaryIO], file_type: str, ...)` |
| `share(doc_id, agent_id, permission, granted_by)` | `set_permissions(doc_id, agent_id, org_id, permissions, granted_by)` |
| `revoke(doc_id, agent_id, permission, revoked_by)` | `set_permissions(...)` (exclude from list) |
| `check_permission(doc_id, agent_id, permission)` | `get_permissions(doc_id, agent_id, org_id)` |
| `list_documents(org_id, agent_id, ...)` | `list_docs(org_id, agent_id, prefix, recursive, ...)` |
| `list_accessible_documents(agent_id, org_id, ...)` | `list_docs(..., permission_check=True)` |
| `get_versions(doc_id, agent_id)` | `get_document_details(..., include_versions=True)` |
| `get_document_permissions(doc_id, agent_id)` | `get_permissions(doc_id, agent_id, org_id)` |
| N/A | `delete_organization(org_id)` (NEW) |
| N/A | `remove_agent(agent_id)` (NEW) |

---

## 🏗️ Architecture Changes

### Entity Model Philosophy

**v1.x**: DocVault stored entity information
```
Organizations: {id, external_id, name, metadata}
Agents: {id, external_id, name, email, agent_type, metadata}
```

**v2.0**: DocVault stores entity references only
```
Organizations: {id, metadata}
Agents: {id, organization_id, metadata}
```

**Why?** Reduce coupling, eliminate data duplication, easier integration with existing identity systems.

### Document Organization

**v1.x**: Flat document structure
```
- document1.pdf
- document2.pdf
- document3.pdf
```

**v2.0**: Hierarchical organization
```
/reports/
  /2025/
    /q1/
      - financial.pdf
      - sales.pdf
    /q2/
      - financial.pdf
/projects/
  /alpha/
    - design.doc
```

### Upload System

**v1.x**: File path only
```python
await vault.upload(file_path="/path/to/file.pdf", ...)
```

**v2.0**: Multiple input types
```python
# File path
await vault.upload(file_path="/path/to/file.pdf", file_type="...", ...)

# Bytes
await vault.upload(file_path=b"...", file_type="...", ...)

# Stream
await vault.upload(file_path=file_handle, file_type="...", ...)
```

---

## 📊 Database Schema Changes

### Removed Columns
```sql
-- Organizations
ALTER TABLE organizations DROP COLUMN external_id;
ALTER TABLE organizations DROP COLUMN name;

-- Agents
ALTER TABLE agents DROP COLUMN external_id;
ALTER TABLE agents DROP COLUMN name;
ALTER TABLE agents DROP COLUMN email;
ALTER TABLE agents DROP COLUMN agent_type;
```

### Added Columns
```sql
-- Documents
ALTER TABLE documents ADD COLUMN prefix VARCHAR(500);
ALTER TABLE documents ADD COLUMN path VARCHAR(1000);
```

### Updated Indexes
```sql
-- Removed
DROP INDEX idx_organizations_external_id;
DROP INDEX idx_agents_external_id;

-- Added
CREATE INDEX idx_documents_prefix ON documents(prefix);
CREATE INDEX idx_documents_path ON documents USING gin(path gin_trgm_ops);
```

---

## 🎯 Common Use Cases

### Use Case 1: Upload with Hierarchy
```python
# Upload to specific location
doc = await vault.upload(
    file_path="/local/path/report.pdf",
    file_type="application/pdf",
    name="Q1 Financial Report",
    organization_id=org_uuid,
    agent_id=agent_uuid,
    prefix="/reports/2025/q1/financial/"
)
# Stored as: /reports/2025/q1/financial/Q1 Financial Report.pdf
```

### Use Case 2: List All Reports for 2025
```python
docs = await vault.list_docs(
    org_id=org_uuid,
    agent_id=agent_uuid,
    prefix="/reports/2025/",
    recursive=True,
    max_depth=None  # Unlimited depth
)
```

### Use Case 3: Grant Multiple Permissions
```python
from doc_vault.database.schemas.acl import Permission

await vault.set_permissions(
    document_id=doc_uuid,
    agent_id=caller_uuid,
    org_id=org_uuid,
    permissions=[
        Permission(agent_id=viewer_uuid, type="READ"),
        Permission(agent_id=editor_uuid, type="WRITE"),
        Permission(agent_id=admin_uuid, type="ADMIN"),
    ],
    granted_by=caller_uuid
)
```

### Use Case 4: Upload from Memory
```python
# Generate PDF in memory
pdf_bytes = generate_pdf_report(data)

# Upload directly
doc = await vault.upload(
    file_path=pdf_bytes,
    file_type="application/pdf",
    name="Generated Report",
    organization_id=org_uuid,
    agent_id=agent_uuid
)
```

### Use Case 5: Replace Document Version
```python
# Update document without creating new version
doc = await vault.upload(
    file_path="/path/to/updated-file.pdf",
    file_type="application/pdf",
    name="Report",  # Same name
    organization_id=org_uuid,
    agent_id=agent_uuid,
    replace_current_version=True  # Delete old, upload new
)
```

---

## 🔍 Troubleshooting

### Problem: TypeError with IDs
```
TypeError: expected UUID, got str
```
**Solution**: Convert strings to UUID
```python
import uuid
org_id = uuid.UUID("your-uuid-string-here")
```

### Problem: Method Not Found
```
AttributeError: 'DocVaultSDK' object has no attribute 'share'
```
**Solution**: Use new permission API
```python
# Old: await vault.share(...)
await vault.set_permissions(...)  # New
```

### Problem: Missing Name Field
```
AttributeError: 'Organization' object has no attribute 'name'
```
**Solution**: Store names externally
```python
# Maintain your own mapping
org_names = {
    org_uuid: "Acme Corp"
}
```

---

## 📚 Resources

| Resource | Location |
|----------|----------|
| Full Implementation Plan | `docs/plan/v2/v2.0-implementation-plan.md` |
| Implementation Checklist | `docs/plan/v2/v2.0-checklist.md` |
| Breaking Changes | `docs/plan/v2/BREAKING_CHANGES.md` |
| API Documentation | `docs/API.md` |
| Examples | `examples/` |

---

## 🚦 Migration Checklist

- [ ] Backup database (`pg_dump`)
- [ ] Update package (`pip install docvault-sdk==2.0.0`)
- [ ] Run migration script (`migrate_v1_to_v2.sql`)
- [ ] Update code: Replace string IDs with UUIDs
- [ ] Update code: Replace old permission methods
- [ ] Update code: Replace old listing methods
- [ ] Update code: Store entity names externally
- [ ] Test: Verify documents accessible
- [ ] Test: Verify permissions work
- [ ] Test: Verify all operations work
- [ ] Deploy to production

---

**Document Version**: 1.0  
**Last Updated**: November 20, 2025
