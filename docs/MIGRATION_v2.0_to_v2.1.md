# Migration Guide: v2.0 → v2.1

**DocVault SDK v2.1.0 Migration Guide**

This guide will help you migrate from DocVault SDK v2.0.0 to v2.1.0.

---

## Table of Contents

1. [Overview](#overview)
2. [Breaking Changes Summary](#breaking-changes-summary)
3. [Step-by-Step Migration](#step-by-step-migration)
4. [API Changes in Detail](#api-changes-in-detail)
5. [Security Changes](#security-changes)
6. [Type Safety Improvements](#type-safety-improvements)
7. [Testing Your Migration](#testing-your-migration)
8. [Rollback Plan](#rollback-plan)

---

## Overview

### What Changed in v2.1?

v2.1 is a **refinement release** that addresses technical debt and API inconsistencies discovered after the v2.0 launch. The focus is on:

- 🔒 **Enhanced Security**: Permission viewing restricted to document owners
- 🎯 **Type Safety**: Pydantic models for type-safe operations
- 📝 **Better Documentation**: Comprehensive exception documentation
- 🧹 **API Cleanup**: Removed unused parameters

### Should You Upgrade?

**Yes, recommended for all v2.0 users.**

**Upgrade Benefits:**
- Enhanced security (prevents permission information leakage)
- Better type safety (catch errors at compile time)
- Improved IDE support (better autocomplete)
- Clearer error messages
- Better documentation

**Upgrade Effort:**
- **Small projects:** 15-30 minutes
- **Medium projects:** 1-2 hours
- **Large projects:** 2-4 hours

Most changes are simple parameter removals. The main consideration is the security enhancement for permission viewing.

---

## Breaking Changes Summary

| Change | Impact | Migration Effort |
|--------|--------|-----------------|
| `get_permissions()` - removed `org_id` parameter | Low | Easy - just remove parameter |
| `set_permissions()` - removed `org_id` parameter | Low | Easy - just remove parameter |
| `get_document_details()` - permission viewing restricted | **Medium** | Review permission checks |
| `set_permissions()` - returns `List[DocumentACL]` | Low | Additive (non-breaking) |
| `get_permissions()` - returns dict with metadata | Low | Structure change (compatible) |

**Total Breaking Changes:** 3 (all parameter-related or security enhancements)

---

## Step-by-Step Migration

### Step 1: Update Dependencies

Update your `pyproject.toml`, `requirements.txt`, or `setup.py`:

```toml
# pyproject.toml
dependencies = [
    "docvault-sdk>=2.1.0,<3.0.0"
]
```

```bash
# Install new version
pip install --upgrade docvault-sdk

# Or with uv
uv pip install --upgrade docvault-sdk
```

**Verify Installation:**
```python
import doc_vault
print(doc_vault.__version__)  # Should print '2.1.0'
```

---

### Step 2: Remove `org_id` from `get_permissions()` Calls

**Find all occurrences:**
```bash
# Search your codebase
grep -r "get_permissions" --include="*.py"
```

**Before (v2.0):**
```python
perms = await vault.get_permissions(
    document_id=doc_id,
    agent_id=agent_id,
    org_id=org_id  # ❌ Remove this line
)
```

**After (v2.1):**
```python
perms = await vault.get_permissions(
    document_id=doc_id,
    agent_id=agent_id  # ✅ org_id removed
)
```

**Return Value Change (Non-Breaking):**
```python
# v2.0 - returned List[Dict]
perms = await vault.get_permissions(...)
for perm in perms:  # Still works!
    print(perm['agent_id'])

# v2.1 - returns Dict with metadata
perms = await vault.get_permissions(...)
print(f"Total: {perms['count']}")  # New: metadata available
for perm in perms['permissions']:  # Permissions in 'permissions' key
    print(perm['agent_id'])
```

**Backward Compatible Access:**
```python
# If you want to keep v2.0 code structure:
perms_list = perms if isinstance(perms, list) else perms.get('permissions', [])
for perm in perms_list:
    print(perm['agent_id'])

# Or update to v2.1 structure (recommended):
for perm in perms['permissions']:
    print(perm['agent_id'])
```

---

### Step 3: Remove `org_id` from `set_permissions()` Calls

**Find all occurrences:**
```bash
grep -r "set_permissions" --include="*.py"
```

**Before (v2.0):**
```python
await vault.set_permissions(
    document_id=doc_id,
    org_id=org_id,  # ❌ Remove this line
    permissions=[
        {"agent_id": str(agent_id), "permission": "READ"}
    ],
    granted_by=admin_id
)
```

**After (v2.1):**
```python
await vault.set_permissions(
    document_id=doc_id,
    permissions=[
        {"agent_id": str(agent_id), "permission": "READ"}
    ],
    granted_by=admin_id
)
```

**Optional: Upgrade to Type-Safe Model (Recommended):**
```python
from doc_vault.database.schemas.permission import PermissionGrant

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
```

**Benefits of PermissionGrant:**
- ✅ Type checking (mypy, IDE autocomplete)
- ✅ Validation at API call time
- ✅ Better error messages
- ✅ Self-documenting code

---

### Step 4: Update Permission Viewing Code

**This is the most important change in v2.1.**

**Find all occurrences:**
```bash
grep -r "include_permissions.*=.*True" --include="*.py"
```

**Security Change:**
Only document owners (agents with ADMIN permission) can view permissions.

**Before (v2.0):**
```python
# Any agent with READ access could do this
details = await vault.get_document_details(
    document_id=doc_id,
    agent_id=any_agent_id,  # Could be non-owner
    include_permissions=True  # Would succeed in v2.0
)
permissions = details.get('permissions', [])
```

**After (v2.1) - Option 1: Check Permission First**
```python
# Check if agent has ADMIN permission
agent_perms = await vault.get_permissions(
    document_id=doc_id,
    agent_id=agent_id
)

is_admin = any(
    p['permission'] == 'ADMIN' 
    for p in agent_perms.get('permissions', [])
)

if is_admin:
    details = await vault.get_document_details(
        document_id=doc_id,
        agent_id=agent_id,
        include_permissions=True
    )
    permissions = details.get('permissions', [])
else:
    print("Only document owners can view permissions")
    permissions = []
```

**After (v2.1) - Option 2: Handle Exception**
```python
try:
    details = await vault.get_document_details(
        document_id=doc_id,
        agent_id=agent_id,
        include_permissions=True
    )
    permissions = details.get('permissions', [])
except PermissionDeniedError:
    # Agent is not owner, cannot view permissions
    print("Only document owners can view permissions")
    permissions = []
```

**After (v2.1) - Option 3: Always Use Owner**
```python
# Ensure you're using document owner's ID
owner_id = await get_document_owner(document_id)  # Your logic

details = await vault.get_document_details(
    document_id=doc_id,
    agent_id=owner_id,  # Always use owner
    include_permissions=True
)
```

**When to Use Each Option:**
- **Option 1** (check first): When you want to show different UI for owners vs non-owners
- **Option 2** (try-except): When you want to attempt and fallback gracefully
- **Option 3** (always owner): When you control the context and know the owner

---

### Step 5: Update Tests

**Update Test Assertions:**

```python
# v2.0 tests
def test_get_permissions_v20():
    perms = await vault.get_permissions(
        document_id=doc_id,
        agent_id=agent_id,
        org_id=org_id
    )
    assert isinstance(perms, list)
    assert len(perms) > 0

# v2.1 tests
async def test_get_permissions_v21():
    perms = await vault.get_permissions(
        document_id=doc_id,
        agent_id=agent_id  # No org_id
    )
    assert isinstance(perms, dict)
    assert 'permissions' in perms
    assert 'count' in perms
    assert len(perms['permissions']) > 0
```

**Add Security Tests:**

```python
async def test_non_owner_cannot_view_permissions():
    """Test that non-owners cannot view permissions."""
    # Create document with owner
    doc = await vault.upload(
        file_input=b"content",
        name="Test Doc",
        organization_id=org_id,
        agent_id=owner_id
    )
    
    # Grant READ to another agent
    await vault.set_permissions(
        document_id=doc.id,
        permissions=[
            PermissionGrant(agent_id=reader_id, permission="READ")
        ],
        granted_by=owner_id
    )
    
    # Reader should NOT be able to view permissions
    with pytest.raises(PermissionDeniedError, match="Only document owners"):
        await vault.get_document_details(
            document_id=doc.id,
            agent_id=reader_id,
            include_permissions=True
        )
    
    # Owner SHOULD be able to view permissions
    details = await vault.get_document_details(
        document_id=doc.id,
        agent_id=owner_id,
        include_permissions=True
    )
    assert 'permissions' in details
    assert len(details['permissions']) > 0
```

---

## API Changes in Detail

### `get_permissions()` Changes

#### Signature Change

**v2.0:**
```python
async def get_permissions(
    document_id: UUID | str,
    agent_id: UUID | str,
    org_id: UUID | str,  # ❌ Removed in v2.1
    permission_filter: Optional[str] = None,  # ❌ Removed in v2.1
) -> List[Dict[str, Any]]
```

**v2.1:**
```python
async def get_permissions(
    document_id: UUID | str,
    agent_id: Optional[UUID | str] = None,  # Now optional
) -> Dict[str, Any]  # Returns dict instead of list
```

#### Return Value Change

**v2.0:**
```python
[
    {
        "agent_id": "uuid-1",
        "permission": "READ",
        "granted_by": "uuid-owner",
        ...
    },
    {
        "agent_id": "uuid-2",
        "permission": "WRITE",
        ...
    }
]
```

**v2.1:**
```python
{
    "document_id": "doc-uuid",
    "permissions": [
        {
            "agent_id": "uuid-1",
            "permission": "READ",
            "granted_by": "uuid-owner",
            "granted_at": "2025-11-21T...",
            "expires_at": None,
            "metadata": {}
        },
        {
            "agent_id": "uuid-2",
            "permission": "WRITE",
            ...
        }
    ],
    "count": 2
}
```

#### Migration Code

```python
def migrate_get_permissions_call(doc_id, agent_id, org_id=None):
    """Helper to migrate get_permissions calls."""
    # v2.0 call
    # perms = await vault.get_permissions(doc_id, agent_id, org_id)
    
    # v2.1 call (org_id removed)
    result = await vault.get_permissions(doc_id, agent_id)
    
    # Extract permissions list for backward compatibility
    perms = result.get('permissions', [])
    
    return perms  # Returns list like v2.0
```

---

### `set_permissions()` Changes

#### Signature Change

**v2.0:**
```python
async def set_permissions(
    document_id: UUID | str,
    org_id: UUID | str,  # ❌ Removed in v2.1
    permissions: List[Dict[str, Any]],
    granted_by: UUID | str,
) -> None
```

**v2.1:**
```python
async def set_permissions(
    document_id: UUID | str,
    permissions: List[PermissionGrant] | List[Dict[str, Any]],  # Type-safe option
    granted_by: UUID | str,
) -> List[DocumentACL]  # Now returns created records
```

#### Using PermissionGrant Model

**Import:**
```python
from doc_vault.database.schemas.permission import PermissionGrant
```

**Model Definition:**
```python
class PermissionGrant(BaseModel):
    agent_id: UUID | str
    permission: str  # Must be: READ, WRITE, DELETE, SHARE, ADMIN
    expires_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
```

**Usage Examples:**

```python
# Simple grant
grant = PermissionGrant(
    agent_id=agent_id,
    permission="READ"
)

# With expiration
from datetime import datetime, timedelta

grant = PermissionGrant(
    agent_id=agent_id,
    permission="READ",
    expires_at=datetime.now() + timedelta(days=7)
)

# With metadata
grant = PermissionGrant(
    agent_id=agent_id,
    permission="WRITE",
    metadata={
        "reason": "project collaboration",
        "project": "Q4 Report"
    }
)

# Bulk grants
grants = [
    PermissionGrant(agent_id=agent1_id, permission="READ"),
    PermissionGrant(agent_id=agent2_id, permission="WRITE"),
    PermissionGrant(agent_id=agent3_id, permission="ADMIN"),
]

result = await vault.set_permissions(
    document_id=doc_id,
    permissions=grants,
    granted_by=owner_id
)

print(f"Created {len(result)} permission records")
```

**Validation Benefits:**

```python
# This will raise ValidationError at API call time (not runtime!)
try:
    grant = PermissionGrant(
        agent_id=agent_id,
        permission="INVALID"  # ❌ Not a valid permission level
    )
except ValidationError as e:
    print(e)  # "Permission must be one of [READ, WRITE, DELETE, SHARE, ADMIN]"

# UUID validation
try:
    grant = PermissionGrant(
        agent_id="not-a-uuid",  # ❌ Invalid UUID
        permission="READ"
    )
except ValidationError as e:
    print(e)  # "agent_id must be a valid UUID string"
```

---

### `get_document_details()` Security Change

#### Permission Viewing Restriction

**v2.0 Behavior:**
- Any agent with READ permission could set `include_permissions=True`
- Returned all document permissions regardless of requester

**v2.1 Behavior:**
- Only agents with ADMIN permission can set `include_permissions=True`
- Non-owners receive `PermissionDeniedError`
- Prevents information leakage about document access

#### Migration Patterns

**Pattern 1: Admin Dashboard**
```python
# Admin viewing all document permissions
async def get_document_admin_view(doc_id, admin_id):
    """Admin view with full permissions."""
    try:
        details = await vault.get_document_details(
            document_id=doc_id,
            agent_id=admin_id,
            include_versions=True,
            include_permissions=True  # Only works if admin_id has ADMIN perm
        )
        return {
            "document": details['document'],
            "versions": details.get('versions', []),
            "permissions": details.get('permissions', []),
            "is_owner": True
        }
    except PermissionDeniedError:
        # Admin doesn't own this document
        details = await vault.get_document_details(
            document_id=doc_id,
            agent_id=admin_id,
            include_versions=True,
            include_permissions=False
        )
        return {
            "document": details['document'],
            "versions": details.get('versions', []),
            "permissions": [],
            "is_owner": False
        }
```

**Pattern 2: User Document List**
```python
# User viewing their accessible documents
async def get_user_documents(user_id, org_id):
    """Get documents user can access (no permission details)."""
    docs = await vault.list_docs(
        organization_id=org_id,
        agent_id=user_id
    )
    
    result = []
    for doc in docs['documents']:
        # Users don't need to see permissions
        details = await vault.get_document_details(
            document_id=doc['id'],
            agent_id=user_id,
            include_versions=False,
            include_permissions=False  # Safe for all users
        )
        result.append(details['document'])
    
    return result
```

**Pattern 3: Conditional Permission View**
```python
# Show permissions only to document owners
async def get_document_with_conditional_perms(doc_id, agent_id):
    """Show permissions if agent is owner."""
    # First, get document without permissions
    details = await vault.get_document_details(
        document_id=doc_id,
        agent_id=agent_id,
        include_permissions=False
    )
    
    # Try to get permissions (will fail if not owner)
    try:
        perms_details = await vault.get_document_details(
            document_id=doc_id,
            agent_id=agent_id,
            include_permissions=True
        )
        details['permissions'] = perms_details.get('permissions', [])
        details['can_view_permissions'] = True
    except PermissionDeniedError:
        details['permissions'] = []
        details['can_view_permissions'] = False
    
    return details
```

---

## Security Changes

### Why This Matters

**Security Issue in v2.0:**
Any agent with READ permission could call `get_document_details(include_permissions=True)` and see who else had access to the document. This is an information leakage vulnerability.

**Example Attack:**
1. Attacker gets READ permission to sensitive document
2. Attacker calls `get_document_details(include_permissions=True)`
3. Attacker learns about other users who have access
4. Attacker can target those users for social engineering

**v2.1 Fix:**
Only document owners (ADMIN permission holders) can view permissions. Non-owners cannot see who else has access.

### Security Best Practices

**1. Principle of Least Privilege**
```python
# ❌ Bad: Granting ADMIN to view permissions
await vault.set_permissions(
    document_id=doc_id,
    permissions=[
        PermissionGrant(agent_id=viewer_id, permission="ADMIN")  # Too much!
    ],
    granted_by=owner_id
)

# ✅ Good: Grant only what's needed
await vault.set_permissions(
    document_id=doc_id,
    permissions=[
        PermissionGrant(agent_id=viewer_id, permission="READ")  # Just right
    ],
    granted_by=owner_id
)
```

**2. Permission Expiration**
```python
from datetime import datetime, timedelta

# Good: Temporary access with expiration
await vault.set_permissions(
    document_id=doc_id,
    permissions=[
        PermissionGrant(
            agent_id=temp_user_id,
            permission="READ",
            expires_at=datetime.now() + timedelta(days=7)  # Expires in 7 days
        )
    ],
    granted_by=owner_id
)
```

**3. Audit Permission Changes**
```python
# Log permission changes
result = await vault.set_permissions(
    document_id=doc_id,
    permissions=[
        PermissionGrant(
            agent_id=new_editor_id,
            permission="WRITE",
            metadata={
                "granted_by_name": "Admin User",
                "reason": "Project collaboration",
                "timestamp": datetime.now().isoformat()
            }
        )
    ],
    granted_by=admin_id
)

# Log to audit trail
for acl in result:
    logger.info(f"Permission granted: {acl.agent_id} - {acl.permission}")
```

---

## Type Safety Improvements

### Why Type Safety Matters

**Before (v2.0) - Runtime Errors:**
```python
# Typo in permission level - fails at runtime!
await vault.set_permissions(
    document_id=doc_id,
    permissions=[
        {"agent_id": agent_id, "permission": "RAED"}  # ❌ Typo! Runtime error
    ],
    granted_by=admin_id
)
```

**After (v2.1) - Compile-Time Errors:**
```python
from doc_vault.database.schemas.permission import PermissionGrant

# Typo in permission level - fails immediately!
try:
    grant = PermissionGrant(
        agent_id=agent_id,
        permission="RAED"  # ❌ Validation error immediately
    )
except ValidationError as e:
    print(e)  # "Permission must be one of [READ, WRITE, DELETE, SHARE, ADMIN]"
```

### IDE Benefits

**Autocomplete:**
```python
# Type "grant." and see all available fields
grant = PermissionGrant(
    agent_id=agent_id,
    permission="READ"
)

# IDE shows:
# - grant.agent_id
# - grant.permission
# - grant.expires_at
# - grant.metadata
```

**Type Hints:**
```python
from typing import List
from doc_vault.database.schemas.permission import PermissionGrant

async def grant_permissions(
    doc_id: UUID,
    grants: List[PermissionGrant]  # IDE knows the type!
) -> None:
    result = await vault.set_permissions(
        document_id=doc_id,
        permissions=grants,
        granted_by=admin_id
    )
    # IDE knows result is List[DocumentACL]
    for acl in result:
        print(acl.permission)  # Autocomplete works!
```

### mypy Integration

**Enable Strict Type Checking:**
```python
# mypy will catch type errors
from doc_vault.database.schemas.permission import PermissionGrant

# ❌ mypy error: Expected UUID | str, got int
grant = PermissionGrant(
    agent_id=12345,  # Type error!
    permission="READ"
)

# ✅ mypy happy
grant = PermissionGrant(
    agent_id=str(uuid.uuid4()),
    permission="READ"
)
```

---

## Testing Your Migration

### Automated Testing Checklist

Create a migration test suite:

```python
# tests/test_v21_migration.py

import pytest
from uuid import uuid4
from doc_vault import DocVaultSDK
from doc_vault.database.schemas.permission import PermissionGrant
from doc_vault.exceptions import PermissionDeniedError

@pytest.mark.asyncio
class TestV21Migration:
    """Test v2.1 migration compatibility."""
    
    async def test_get_permissions_no_org_id(self, vault, doc_id, agent_id):
        """Test get_permissions works without org_id."""
        # Should work without org_id parameter
        perms = await vault.get_permissions(
            document_id=doc_id,
            agent_id=agent_id
        )
        
        # Returns dict with metadata
        assert isinstance(perms, dict)
        assert 'permissions' in perms
        assert 'count' in perms
    
    async def test_set_permissions_no_org_id(self, vault, doc_id, agent_id, admin_id):
        """Test set_permissions works without org_id."""
        # Should work without org_id parameter
        result = await vault.set_permissions(
            document_id=doc_id,
            permissions=[
                {"agent_id": str(agent_id), "permission": "READ"}
            ],
            granted_by=admin_id
        )
        
        # Returns list of ACL records
        assert isinstance(result, list)
        assert len(result) > 0
    
    async def test_set_permissions_with_model(self, vault, doc_id, agent_id, admin_id):
        """Test set_permissions with PermissionGrant model."""
        result = await vault.set_permissions(
            document_id=doc_id,
            permissions=[
                PermissionGrant(agent_id=agent_id, permission="WRITE")
            ],
            granted_by=admin_id
        )
        
        assert isinstance(result, list)
        assert len(result) > 0
    
    async def test_permission_viewing_security(self, vault, doc_id, owner_id, reader_id):
        """Test that non-owners cannot view permissions."""
        # Grant READ to reader
        await vault.set_permissions(
            document_id=doc_id,
            permissions=[
                PermissionGrant(agent_id=reader_id, permission="READ")
            ],
            granted_by=owner_id
        )
        
        # Owner can view permissions
        details = await vault.get_document_details(
            document_id=doc_id,
            agent_id=owner_id,
            include_permissions=True
        )
        assert 'permissions' in details
        
        # Reader cannot view permissions
        with pytest.raises(PermissionDeniedError):
            await vault.get_document_details(
                document_id=doc_id,
                agent_id=reader_id,
                include_permissions=True
            )
```

### Manual Testing Checklist

- [ ] All `get_permissions()` calls work without `org_id`
- [ ] All `set_permissions()` calls work without `org_id`
- [ ] `set_permissions()` with PermissionGrant model works
- [ ] `get_document_details(include_permissions=True)` only works for owners
- [ ] Non-owners receive clear error messages
- [ ] Return values are handled correctly (dict vs list)
- [ ] Existing tests pass
- [ ] New security tests pass

### Integration Testing

```bash
# Run full test suite
pytest tests/ -v

# Run only migration tests
pytest tests/test_v21_migration.py -v

# Run with coverage
pytest tests/ --cov=doc_vault --cov-report=html
```

---

## Rollback Plan

### If You Need to Rollback to v2.0

**1. Revert Dependency:**
```toml
# pyproject.toml
dependencies = [
    "docvault-sdk>=2.0.0,<2.1.0"
]
```

```bash
pip install "docvault-sdk>=2.0.0,<2.1.0"
```

**2. Revert Code Changes:**
```bash
# If using git
git checkout <commit-before-migration>

# Or manually revert:
# - Add back org_id parameters
# - Remove PermissionGrant imports
# - Revert get_document_details security changes
```

**3. What to Keep from v2.1:**
Even if you rollback, consider keeping:
- Comprehensive exception handling
- Security checks for permission viewing (manual implementation)
- Better error messages

---

## Common Issues and Solutions

### Issue 1: "missing required argument: 'org_id'"

**Error:**
```python
TypeError: get_permissions() missing required argument: 'org_id'
```

**Cause:** Using v2.1 SDK with v2.0 code.

**Solution:** Remove the `org_id` parameter from the call.

---

### Issue 2: "PermissionDeniedError: Only document owners can view permissions"

**Error:**
```python
PermissionDeniedError: Only document owners (ADMIN permission) can view permissions
```

**Cause:** Non-owner agent attempting to view permissions in v2.1.

**Solutions:**

**Option A: Check permission first**
```python
# Check if agent is owner before requesting permissions
agent_perms = await vault.get_permissions(document_id=doc_id, agent_id=agent_id)
is_owner = any(p['permission'] == 'ADMIN' for p in agent_perms['permissions'])

if is_owner:
    details = await vault.get_document_details(
        document_id=doc_id,
        agent_id=agent_id,
        include_permissions=True
    )
else:
    # Handle non-owner case
    pass
```

**Option B: Handle exception**
```python
try:
    details = await vault.get_document_details(
        document_id=doc_id,
        agent_id=agent_id,
        include_permissions=True
    )
except PermissionDeniedError:
    # Handle non-owner case
    pass
```

---

### Issue 3: "ValidationError: Permission must be one of..."

**Error:**
```python
ValidationError: Permission must be one of [READ, WRITE, DELETE, SHARE, ADMIN]
```

**Cause:** Invalid permission level in PermissionGrant.

**Solution:** Use only valid permission levels:
```python
# Valid permissions
VALID_PERMISSIONS = ["READ", "WRITE", "DELETE", "SHARE", "ADMIN"]

# Use one of these
grant = PermissionGrant(
    agent_id=agent_id,
    permission="READ"  # Must be from VALID_PERMISSIONS
)
```

---

### Issue 4: "get_permissions() returns dict instead of list"

**Error:**
```python
# v2.0 code expecting list
for perm in perms:  # TypeError: dict is not iterable
    ...
```

**Cause:** v2.1 returns dict with metadata instead of list.

**Solution:**
```python
# v2.1 code
perms = await vault.get_permissions(doc_id, agent_id)

# Access permissions list
for perm in perms['permissions']:  # Add ['permissions']
    print(perm['agent_id'])
```

---

## FAQ

### Q: Is v2.1 backward compatible with v2.0?

**A:** Mostly yes, with minor breaking changes:
- Parameter removals (org_id) are breaking
- Security enhancement for permission viewing is breaking
- Return value changes are mostly compatible

### Q: Do I need to update my database schema?

**A:** No, v2.1 uses the same database schema as v2.0. No migrations required.

### Q: Can I use both dict and PermissionGrant in set_permissions()?

**A:** Yes! v2.1 accepts both formats:
```python
# Both work
await vault.set_permissions(permissions=[{"agent_id": ..., "permission": "READ"}], ...)
await vault.set_permissions(permissions=[PermissionGrant(...)], ...)
```

### Q: What if I don't want to use PermissionGrant?

**A:** It's optional! You can continue using dicts. PermissionGrant just provides better type safety.

### Q: Will v2.0 code break in v2.1?

**A:** Not entirely. Most code will work with warnings. The main changes are:
1. Remove `org_id` parameters (required)
2. Handle permission viewing security (required if using `include_permissions=True`)
3. Optionally adopt PermissionGrant (recommended but not required)

### Q: How long will v2.0 be supported?

**A:** v2.0 is superseded by v2.1. We recommend upgrading as soon as possible for security enhancements.

### Q: Can I gradually migrate?

**A:** Yes! You can:
1. Update dependencies to v2.1
2. Fix parameter removals (quick)
3. Fix permission viewing (medium)
4. Optionally adopt PermissionGrant (gradual)

---

## Support

### Need Help?

- **Documentation:** [docs/API.md](./API.md)
- **Examples:** [examples/](../examples/)
- **Issues:** [GitHub Issues](https://github.com/your-org/doc_vault/issues)
- **Discussions:** [GitHub Discussions](https://github.com/your-org/doc_vault/discussions)

### Report Migration Issues

If you encounter issues during migration, please report them with:
1. Your v2.0 code
2. What you changed for v2.1
3. Error message or unexpected behavior
4. DocVault version (`import doc_vault; print(doc_vault.__version__)`)

---

**Good luck with your migration! 🚀**

The v2.1 improvements will make your code safer, more maintainable, and easier to understand.
