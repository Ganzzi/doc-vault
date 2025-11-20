# DocVault v2.0 Breaking Changes Summary

**Version**: 2.0.0  
**Date**: November 20, 2025

---

## Overview

DocVault v2.0 introduces significant breaking changes that require code and database migrations. This document provides a concise summary of all breaking changes and their impact.

⚠️ **WARNING**: v2.0 is **NOT** backwards compatible with v1.x

---

## 🔴 Critical Breaking Changes

### 1. Entity Identification System

**Change**: Organizations and Agents now use external UUIDs as primary keys, removing the `external_id` string field entirely.

**Impact**: 
- Database schema change required
- All API calls must use UUIDs instead of string identifiers
- Existing integrations must be updated

**v1.x (OLD)**:
```python
await vault.register_organization(external_id="org-123", name="My Org")
await vault.register_agent(
    external_id="agent-456",
    organization_id="org-123",
    name="Agent Name"
)
```

**v2.0 (NEW)**:
```python
import uuid

org_id = uuid.uuid4()
agent_id = uuid.uuid4()

await vault.register_organization(id=org_id)
await vault.register_agent(id=agent_id, organization_id=org_id)
```

---

### 2. Simplified Entity Schema

**Change**: Organizations and Agents no longer store names and metadata. They are pure reference entities.

**Removed Fields**:
- Organizations: `external_id`, `name`
- Agents: `external_id`, `name`, `email`, `agent_type`

**Impact**:
- Name and metadata must be stored in external systems
- Migration script must preserve or migrate this data elsewhere
- Display names must come from your application, not DocVault

**Philosophy**: DocVault is now a document management layer, not an identity management system.

---

### 3. Permission API Overhaul

**Change**: Multiple permission methods replaced with two consolidated methods.

**Removed Methods**:
```python
# ❌ NO LONGER AVAILABLE
await vault.share(doc_id, agent_id, permission, granted_by)
await vault.revoke(doc_id, agent_id, permission, revoked_by)
await vault.check_permission(doc_id, agent_id, permission)
await vault.list_accessible_documents(agent_id, org_id)
await vault.get_document_permissions(doc_id, agent_id)
```

**New Methods**:
```python
# ✅ NEW API
# Get all permissions for a document
permissions = await vault.get_permissions(
    document_id=doc_id,
    agent_id=agent_id,
    org_id=org_id
)

# Set/update permissions (bulk operation)
await vault.set_permissions(
    document_id=doc_id,
    agent_id=agent_id,
    org_id=org_id,
    permissions=[
        Permission(agent_id=agent1_id, type="READ"),
        Permission(agent_id=agent2_id, type="WRITE"),
    ],
    granted_by=granter_id
)
```

---

### 4. Version Management Consolidation

**Change**: Removed separate version query methods in favor of unified document details.

**Removed Methods**:
```python
# ❌ NO LONGER AVAILABLE
await vault.get_versions(doc_id, agent_id)
await vault.get_version_info(doc_id, version_number, agent_id)
```

**New Method**:
```python
# ✅ NEW API
details = await vault.get_document_details(
    document_id=doc_id,
    org_id=org_id,
    agent_id=agent_id,
    include_versions=True,  # Include version history
    include_permissions=True  # Include permissions (if owner)
)
# Access: details.versions, details.permissions
```

---

## 🟡 Major API Changes

### 5. Enhanced Upload API

**Change**: Upload now accepts multiple input types and supports version replacement.

**v1.x (OLD)**:
```python
doc = await vault.upload(
    file_path="/path/to/file.pdf",
    name="Document",
    organization_id="org-123",
    agent_id="agent-456"
)
```

**v2.0 (NEW)**:
```python
# File path (same as before)
doc = await vault.upload(
    file_path="/path/to/file.pdf",
    file_type="application/pdf",
    name="Document",
    organization_id=org_uuid,
    agent_id=agent_uuid,
    prefix="/reports/2025/",  # NEW: hierarchical organization
    replace_current_version=False  # NEW: replace instead of version
)

# Bytes (NEW)
doc = await vault.upload(
    file_path=file_bytes,
    file_type="application/pdf",
    name="Document",
    organization_id=org_uuid,
    agent_id=agent_uuid
)

# Binary stream (NEW)
with open("file.pdf", "rb") as f:
    doc = await vault.upload(
        file_path=f,
        file_type="application/pdf",
        name="Document",
        organization_id=org_uuid,
        agent_id=agent_uuid
    )
```

---

### 6. Hierarchical Document Organization

**Change**: Documents can now be organized hierarchically using prefixes.

**New Feature**:
```python
# Upload with prefix
doc = await vault.upload(
    file_path=file_path,
    file_type="application/pdf",
    name="financial-report.pdf",
    prefix="/reports/2025/q1/",  # Hierarchical path
    organization_id=org_uuid,
    agent_id=agent_uuid
)

# List documents by prefix
docs = await vault.list_docs(
    prefix="/reports/2025/",
    org_id=org_uuid,
    agent_id=agent_uuid,
    recursive=True,  # Include subdirectories
    max_depth=3  # Limit recursion depth
)
```

---

### 7. New Document Listing API

**Change**: Document listing now supports hierarchical navigation and advanced filtering.

**v1.x (OLD)**:
```python
docs = await vault.list_documents(
    organization_id="org-123",
    agent_id="agent-456",
    status="active",
    tags=["important"]
)
```

**v2.0 (NEW)**:
```python
docs = await vault.list_docs(
    org_id=org_uuid,
    agent_id=agent_uuid,
    prefix="/reports/",  # NEW: filter by prefix
    recursive=True,  # NEW: include subdirectories
    max_depth=5,  # NEW: limit recursion
    permission_check=True,  # NEW: only accessible docs
    limit=50,
    offset=0
)
```

---

### 8. Organization & Agent Deletion

**Change**: Can now delete organizations and remove agents.

**New Methods**:
```python
# Delete organization (must be empty or use force=True)
await vault.delete_organization(org_id=org_uuid)

# Remove agent from system
await vault.remove_agent(agent_id=agent_uuid)
```

---

## 📊 Database Schema Changes

### Organizations Table

| Change | Field | Action |
|--------|-------|--------|
| ❌ Removed | `external_id` | Deleted |
| ❌ Removed | `name` | Deleted |
| ✅ Changed | `id` | Now accepts external UUIDs |

### Agents Table

| Change | Field | Action |
|--------|-------|--------|
| ❌ Removed | `external_id` | Deleted |
| ❌ Removed | `name` | Deleted |
| ❌ Removed | `email` | Deleted |
| ❌ Removed | `agent_type` | Deleted |
| ✅ Changed | `id` | Now accepts external UUIDs |

### Documents Table

| Change | Field | Action |
|--------|-------|--------|
| ✅ Added | `prefix` | VARCHAR(500), hierarchical path |
| ✅ Added | `path` | VARCHAR(1000), full document path |

### Indexes

| Change | Index | Action |
|--------|-------|--------|
| ❌ Removed | `idx_organizations_external_id` | Deleted |
| ❌ Removed | `idx_agents_external_id` | Deleted |
| ✅ Added | `idx_documents_prefix` | Created |
| ✅ Added | `idx_documents_path` | Created (GIN with trigram) |

---

## 🔄 Migration Path

### Step 1: Backup Your Data
```bash
pg_dump doc_vault > doc_vault_v1_backup.sql
```

### Step 2: Update Dependencies
```bash
pip install docvault-sdk==2.0.0
```

### Step 3: Run Database Migration
```bash
# Migration script provided in v2.0 release
psql doc_vault < migrate_v1_to_v2.sql
```

### Step 4: Update Your Code

1. **Replace string IDs with UUIDs**
2. **Update all API calls to use new methods**
3. **Store entity names externally if needed**
4. **Update permission management code**
5. **Update document listing code**

### Step 5: Test Thoroughly
- Verify all documents accessible
- Verify all permissions preserved
- Verify all operations work

---

## ⚠️ Impact Assessment

### High Impact (Requires Code Changes)
- ✅ All organization/agent registration code
- ✅ All permission management code
- ✅ All document listing code
- ✅ All methods using string IDs

### Medium Impact (May Require Changes)
- ⚡ Document upload code (if using advanced features)
- ⚡ Version management code
- ⚡ Search and filtering code

### Low Impact (Minimal Changes)
- 🔹 Download operations
- 🔹 Basic metadata operations
- 🔹 Configuration

---

## 🆘 Common Migration Issues

### Issue 1: String IDs Still in Use
**Error**: `TypeError: expected UUID, got str`

**Solution**: Convert all string IDs to UUIDs:
```python
import uuid
org_id = uuid.UUID("your-org-uuid-here")
```

### Issue 2: Permission Method Not Found
**Error**: `AttributeError: 'DocVaultSDK' object has no attribute 'share'`

**Solution**: Use new permission API:
```python
# Old: await vault.share(...)
# New: await vault.set_permissions(...)
```

### Issue 3: Missing Entity Names
**Error**: Organization/Agent names no longer available

**Solution**: Store names in your application:
```python
# Your application's organization mapping
org_names = {
    uuid.UUID("..."): "Acme Corp",
    uuid.UUID("..."): "Widgets Inc"
}
```

---

## 📚 Resources

- **Full Implementation Plan**: `docs/plan/v2/v2.0-implementation-plan.md`
- **Migration Checklist**: `docs/plan/v2/v2.0-checklist.md`
- **API Documentation**: `docs/API.md`
- **Migration Guide**: `docs/MIGRATION_V1_TO_V2.md` (to be created)
- **Examples**: `examples/` directory

---

## 🤝 Support

If you encounter issues during migration:
1. Check the migration guide: `docs/MIGRATION_V1_TO_V2.md`
2. Review the examples: `examples/`
3. Open an issue: [GitHub Issues](https://github.com/docvault/doc-vault/issues)
4. Contact support: team@docvault.dev

---

## 📅 Support Timeline

- **v1.x**: Security fixes only until May 20, 2026 (6 months after v2.0 release)
- **v2.0**: Full support and active development

---

**Document Version**: 1.0  
**Last Updated**: November 20, 2025  
**Status**: Final
