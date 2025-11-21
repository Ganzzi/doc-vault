# Migration Guide: DocVault v2.1 to v2.2

**Version**: 2.2.0  
**Released**: December 5, 2025  
**Migration Difficulty**: Medium  
**Estimated Time**: 30-60 minutes for most projects

---

## Table of Contents

1. [Overview](#overview)
2. [Breaking Changes](#breaking-changes)
3. [Migration Steps](#migration-steps)
4. [Non-Breaking Changes](#non-breaking-changes)
5. [Troubleshooting](#troubleshooting)
6. [FAQ](#faq)

---

## Overview

DocVault v2.2 focuses on **type safety** and **API consistency**. The main improvements are:

- ✅ **Type-Safe Response Models**: All methods return explicit Pydantic models instead of `Dict[str, Any]`
- ✅ **Smart Upload Detection**: Automatic detection of file paths vs. text content
- ✅ **Model-Only Permissions**: `set_permissions()` now only accepts `PermissionGrant` models
- ✅ **Simplified Codebase**: Removed legacy v1.x compatibility code

### Who Should Migrate?

- **Required**: Projects using `set_permissions()` with dict inputs
- **Recommended**: All projects to benefit from type safety and IDE autocomplete
- **Optional**: Projects that work fine with v2.1 and don't need type hints

---

## Breaking Changes

### 1. Response Types Changed (Dict → Models)

**Impact**: Medium - Requires code updates if accessing dict keys

All methods that returned `Dict[str, Any]` now return explicit Pydantic models.

#### Affected Methods

| Method | Old Return Type | New Return Type |
|--------|----------------|-----------------|
| `list_docs()` | `Dict[str, Any]` | `DocumentListResponse` |
| `search()` | `Dict[str, Any]` | `SearchResponse` |
| `get_document_details()` | `Dict[str, Any]` | `DocumentDetails` |
| `get_permissions()` | `Dict[str, Any]` | `PermissionListResponse` |
| `set_permissions()` | `List[Any]` | `List[DocumentACL]` |
| `transfer_ownership()` | (no type hint) | `OwnershipTransferResponse` |

#### Migration Required

**Before (v2.1):**
```python
# Dict-style access
result = await vault.list_docs(org_id=org, agent_id=agent)
docs = result["documents"]  # Access dict key
total = result["pagination"]["total"]  # Nested dict access
```

**After (v2.2):**
```python
# Model attribute access
result = await vault.list_docs(org_id=org, agent_id=agent)
docs = result.documents  # Access model attribute ✅
total = result.pagination.total  # Type-safe access ✅
```

**If you need dict format** (for compatibility):
```python
result = await vault.list_docs(org_id=org, agent_id=agent)
result_dict = result.model_dump()  # Convert to dict
docs = result_dict["documents"]  # Works like v2.1
```

---

### 2. set_permissions() Signature Changed

**Impact**: High - Breaking change for dict-based permission calls

The `set_permissions()` method now **only accepts** `List[PermissionGrant]` models. Dict inputs are no longer supported.

#### Migration Required

**Before (v2.1):**
```python
# Dict-based permissions (NO LONGER SUPPORTED)
await vault.set_permissions(
    document_id=doc_id,
    permissions=[
        {"agent_id": agent1, "permission": "READ"},  # ❌ Dict
        {"agent_id": agent2, "permission": "WRITE"},  # ❌ Dict
    ],
    granted_by=admin,
)
```

**After (v2.2):**
```python
from doc_vault.database.schemas import PermissionGrant

# Model-based permissions (REQUIRED)
await vault.set_permissions(
    document_id=doc_id,
    permissions=[
        PermissionGrant(agent_id=agent1, permission="READ"),  # ✅ Model
        PermissionGrant(agent_id=agent2, permission="WRITE"),  # ✅ Model
    ],
    granted_by=admin,
)
```

**Migration Helper Function:**
```python
from doc_vault.database.schemas import PermissionGrant

def migrate_permissions(dict_perms: list[dict]) -> list[PermissionGrant]:
    """Convert v2.1 dict permissions to v2.2 models."""
    return [PermissionGrant(**p) for p in dict_perms]

# Usage
old_perms = [
    {"agent_id": agent1, "permission": "READ"},
    {"agent_id": agent2, "permission": "WRITE"},
]
new_perms = migrate_permissions(old_perms)
await vault.set_permissions(document_id=doc_id, permissions=new_perms, granted_by=admin)
```

---

### 3. _resolve_external_ids() Removed (Internal)

**Impact**: Low - Only affects code using internal methods

The internal method `_resolve_external_ids()` has been removed. This was a v1.x legacy method that's no longer needed in v2.x.

#### Who's Affected?

- Projects directly calling `vault._resolve_external_ids()` (rare, internal API)
- Most users are **not affected**

#### Migration Required

If you were using this internal method, replace it with direct UUID handling:

**Before (v2.1):**
```python
# Using internal method (DEPRECATED)
org_uuid, agent_uuid = await vault._resolve_external_ids(
    organization_id=org_ext_id,
    agent_id=agent_ext_id,
)
```

**After (v2.2):**
```python
# Use UUIDs directly (v2.x design)
# Organizations and agents already use UUIDs as primary keys in v2.x
org_uuid = org_id  # Already a UUID in v2.x
agent_uuid = agent_id  # Already a UUID in v2.x
```

---

## Migration Steps

### Step 1: Update Response Handling

**Estimate**: 10-20 minutes

#### 1.1 Update list_docs() Calls

```python
# Before
result = await vault.list_docs(org_id=org, agent_id=agent, limit=10)
for doc in result["documents"]:
    print(doc.name)

# After
result = await vault.list_docs(org_id=org, agent_id=agent, limit=10)
for doc in result.documents:  # Change to attribute access
    print(doc.name)
```

#### 1.2 Update search() Calls

```python
# Before
result = await vault.search(query="report", org_id=org, agent_id=agent)
total = result["pagination"]["total"]

# After
result = await vault.search(query="report", org_id=org, agent_id=agent)
total = result.pagination.total  # Change to attribute access
```

#### 1.3 Update get_document_details() Calls

```python
# Before
details = await vault.get_document_details(doc_id, agent, include_versions=True)
doc = details["document"]
versions = details["versions"]

# After
details = await vault.get_document_details(doc_id, agent, include_versions=True)
doc = details.document  # Change to attribute access
versions = details.versions
```

---

### Step 2: Update Permission Calls

**Estimate**: 10-15 minutes

#### 2.1 Import PermissionGrant

```python
from doc_vault.database.schemas import PermissionGrant
```

#### 2.2 Convert Dict Permissions to Models

**Option A: Manual Conversion** (Recommended)
```python
# Before
perms = [
    {"agent_id": agent1, "permission": "READ"},
    {"agent_id": agent2, "permission": "WRITE"},
]

# After
perms = [
    PermissionGrant(agent_id=agent1, permission="READ"),
    PermissionGrant(agent_id=agent2, permission="WRITE"),
]
```

**Option B: Bulk Conversion** (For large codebases)
```python
# Helper function for migration
def to_permission_grants(dict_list: list[dict]) -> list[PermissionGrant]:
    return [PermissionGrant(**d) for d in dict_list]

# Use in migration
old_perms = [{"agent_id": a, "permission": "READ"} for a in agents]
new_perms = to_permission_grants(old_perms)
await vault.set_permissions(doc_id, new_perms, admin)
```

---

### Step 3: Leverage Text Content Upload (New Feature)

**Estimate**: 5 minutes (optional)

v2.2 adds smart detection for text content uploads. You no longer need temp files for text!

#### 3.1 Replace Temp File Uploads

**Before (v2.1):**
```python
import tempfile
import os

# Had to create temp file
with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
    f.write("My document content")
    temp_path = f.name

doc = await vault.upload(
    file_input=temp_path,
    name="my_doc.txt",
    org_id=org,
    agent_id=agent,
)
os.unlink(temp_path)  # Manual cleanup
```

**After (v2.2):**
```python
# Direct text upload - much cleaner!
doc = await vault.upload(
    file_input="My document content",  # Just pass the text
    name="my_doc.txt",
    org_id=org,
    agent_id=agent,
)
```

#### 3.2 How Text Detection Works

```python
# File path (if exists) → reads file
doc = await vault.upload(
    file_input="/path/to/file.pdf",  # File exists → read file
    ...
)

# Text content (if path doesn't exist) → uses text
doc = await vault.upload(
    file_input="Hello, world!",  # Not a file → treat as text
    ...
)

# Bytes → works as before
doc = await vault.upload(
    file_input=b"Binary content",
    ...
)

# BinaryIO → works as before
with open("file.pdf", "rb") as f:
    doc = await vault.upload(file_input=f, ...)
```

---

### Step 4: Add Type Hints (Optional but Recommended)

**Estimate**: 10-20 minutes

#### 4.1 Import Response Models

```python
from doc_vault.database.schemas import (
    DocumentListResponse,
    SearchResponse,
    DocumentDetails,
    PermissionListResponse,
    OwnershipTransferResponse,
)
```

#### 4.2 Add Return Type Hints

```python
# Before (v2.1)
async def get_my_documents(vault, org, agent):  # No type hints
    result = await vault.list_docs(org_id=org, agent_id=agent)
    return result

# After (v2.2)
async def get_my_documents(
    vault: DocVaultSDK,
    org: UUID,
    agent: UUID
) -> DocumentListResponse:  # Explicit return type
    result = await vault.list_docs(org_id=org, agent_id=agent)
    return result  # Type checker validates this!
```

#### 4.3 Benefits

```python
async def process_documents(vault: DocVaultSDK, org: UUID, agent: UUID) -> int:
    result = await vault.list_docs(org_id=org, agent_id=agent)
    
    # IDE autocomplete works!
    total = result.pagination.total  # ✅ Suggested by IDE
    docs = result.documents  # ✅ Type-checked
    
    # Type errors caught at development time
    # result.documnets  # ❌ Typo caught by type checker
    
    return total
```

---

## Non-Breaking Changes

### 1. agent_id Type Expansion

Four methods now accept `str | UUID` instead of `str` only. This is **backward compatible**.

**Methods Updated:**
- `download(document_id, agent_id, ...)`
- `update_metadata(document_id, agent_id, ...)`
- `delete(document_id, agent_id, ...)`
- `restore_version(document_id, version_number, agent_id, ...)`

**Before and After (both work):**
```python
# v2.1 - str only
await vault.download(doc_id, agent_id="agent-123", ...)

# v2.2 - str or UUID (backward compatible)
await vault.download(doc_id, agent_id="agent-123", ...)  # ✅ Still works
await vault.download(doc_id, agent_id=agent_uuid, ...)  # ✅ Also works
```

### 2. Response Model Serialization

All response models can be converted back to dicts for compatibility:

```python
result = await vault.list_docs(org_id=org, agent_id=agent)

# Model format (v2.2 style)
docs = result.documents

# Dict format (v2.1 compatibility)
result_dict = result.model_dump()
docs = result_dict["documents"]

# JSON format
result_json = result.model_dump_json()
```

---

## Troubleshooting

### Issue 1: AttributeError on Response

**Error:**
```python
AttributeError: 'DocumentListResponse' object has no attribute 'get'
```

**Cause:** Trying to use dict methods on model objects

**Fix:**
```python
# Wrong
result.get("documents")  # ❌ Models don't have .get()

# Right
result.documents  # ✅ Use attribute access
```

### Issue 2: TypeError in set_permissions()

**Error:**
```python
TypeError: set_permissions() argument 'permissions' expected List[PermissionGrant], got list[dict]
```

**Cause:** Passing dicts instead of PermissionGrant models

**Fix:**
```python
from doc_vault.database.schemas import PermissionGrant

# Wrong
perms = [{"agent_id": agent, "permission": "READ"}]  # ❌ Dict

# Right
perms = [PermissionGrant(agent_id=agent, permission="READ")]  # ✅ Model
```

### Issue 3: Upload Treats File Path as Text

**Symptom:** File path string is uploaded as text content instead of file

**Cause:** File path doesn't exist or is a relative path

**Fix:**
```python
# Problem: Relative path
doc = await vault.upload(file_input="data/file.pdf", ...)  # May not exist

# Solution: Use absolute path
from pathlib import Path
file_path = Path("data/file.pdf").resolve()
doc = await vault.upload(file_input=str(file_path), ...)
```

### Issue 4: Missing Type Hints in IDE

**Symptom:** No autocomplete for response model attributes

**Cause:** IDE not recognizing Pydantic models

**Fix:**
1. Ensure you have Pydantic 2.x installed
2. Update your IDE's type checker settings
3. Restart IDE/language server

**PyCharm:**
```
Settings → Python Integrated Tools → Type Checker: Pyright
```

**VSCode:**
```json
// settings.json
{
  "python.analysis.typeCheckingMode": "basic"
}
```

---

## FAQ

### Q1: Do I have to migrate immediately?

**A:** No, but it's recommended. v2.1 will continue to work, but v2.2 provides better type safety and developer experience.

### Q2: Can I use both dict and model styles?

**A:** For responses, yes (use `.model_dump()`). For `set_permissions()`, no - models only.

### Q3: Will this break my existing tests?

**A:** Possibly. Update tests to use attribute access instead of dict keys. See [Step 1](#step-1-update-response-handling).

### Q4: How do I know if I'm affected?

**A:** Search your codebase for:
- `result["documents"]` or similar dict access on SDK responses
- `set_permissions()` calls with dict inputs
- Direct calls to `_resolve_external_ids()`

### Q5: What if I have 100+ permission calls to update?

**A:** Use a migration script:

```python
# migration_helper.py
from doc_vault.database.schemas import PermissionGrant

def migrate_permission_call(agent_perms: dict[str, str]) -> list[PermissionGrant]:
    """Convert dict permissions to models."""
    return [
        PermissionGrant(agent_id=agent_id, permission=perm)
        for agent_id, perm in agent_perms.items()
    ]

# Before
await vault.set_permissions(doc, [{"agent_id": a, "permission": "READ"}], admin)

# After (using helper)
perms = migrate_permission_call({"agent-1": "READ", "agent-2": "WRITE"})
await vault.set_permissions(doc, perms, admin)
```

### Q6: Are there performance implications?

**A:** Minimal. Pydantic model overhead is negligible (<1ms per operation).

### Q7: Can I still access nested fields?

**A:** Yes, models support nested access:

```python
result = await vault.list_docs(...)

# Nested attribute access
total = result.pagination.total
has_more = result.pagination.has_more

# Or convert to dict
result_dict = result.model_dump()
total = result_dict["pagination"]["total"]
```

### Q8: What about serialization to JSON?

**A:** Models have built-in JSON support:

```python
result = await vault.list_docs(...)

# To JSON string
json_str = result.model_dump_json()

# To dict (for json.dumps)
result_dict = result.model_dump()
import json
json_str = json.dumps(result_dict)
```

---

## Summary Checklist

Use this checklist to track your migration:

- [ ] Updated `list_docs()` calls to use model attributes
- [ ] Updated `search()` calls to use model attributes
- [ ] Updated `get_document_details()` calls to use model attributes
- [ ] Updated `get_permissions()` calls to use model attributes
- [ ] Converted all `set_permissions()` dict inputs to `PermissionGrant` models
- [ ] Removed direct calls to `_resolve_external_ids()` (if any)
- [ ] Leveraged text content upload for string data (optional)
- [ ] Added type hints to functions using SDK (optional)
- [ ] Updated tests to use model attributes
- [ ] Ran type checker (mypy/pyright) to catch issues
- [ ] Tested application end-to-end

---

## Support

If you encounter issues during migration:

1. **Check this guide** for common problems
2. **Search GitHub Issues** for similar problems
3. **Create an issue** with label `v2.2-migration`
4. **Contact support** at team@docvault.dev

---

**Last Updated**: December 5, 2025  
**Version**: 2.2.0  
**Need Help?** Open an issue on GitHub
