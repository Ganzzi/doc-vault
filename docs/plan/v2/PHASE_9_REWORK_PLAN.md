# Phase 9 Rework Implementation Plan

**Date**: November 20, 2025  
**Status**: Ready to Execute  
**Estimated Time**: 3-5 days  
**Approach**: Option A - True Breaking Changes

---

## Overview

This plan details the step-by-step process to rework Phase 9 (Core SDK Integration) to match the v2.0 plan specifications, creating true breaking changes.

---

## Task Breakdown

### Task 1: Remove v1.x Methods (1-2 hours)

**File**: `src/doc_vault/core.py`

**Methods to DELETE**:

```python
# Lines to remove:
1. share()                       # lines ~400-434
2. revoke()                      # lines ~436-465
3. check_permission()            # lines ~467-495
4. list_accessible_documents()   # lines ~497-527
5. get_document_permissions()    # lines ~529-554
6. get_versions()                # lines ~556-583
7. get_version_info()            # lines ~618-646
```

**Verification**:
- [ ] All 7 methods removed
- [ ] No references to these methods in core.py
- [ ] File compiles without errors

---

### Task 2: Rename v2.0 Methods (2-3 hours)

**File**: `src/doc_vault/core.py`

**Renames Required**:

| Current Name | New Name | Lines |
|--------------|----------|-------|
| `upload_enhanced()` | `upload()` | ~766-812 |
| `list_documents_paginated()` | `list_docs()` | ~844-886 |
| `search_documents_enhanced()` | `search()` | ~888-929 |
| `set_permissions_bulk()` | `set_permissions()` | ~931-957 |
| `get_permissions_detailed()` | `get_permissions()` | ~959-982 |
| `replace_document_content()` | `replace()` | ~1012-1050 |

**Strategy**:
1. Delete old v1.x method (e.g., old `upload()`)
2. Rename v2.0 method to take its place (e.g., `upload_enhanced()` → `upload()`)
3. Update docstrings to reflect v2.0 behavior

**Verification**:
- [ ] All 6 methods renamed
- [ ] Old v1.x versions removed
- [ ] Docstrings updated
- [ ] File compiles without errors

---

### Task 3: Add Missing Methods (1 hour)

**File**: `src/doc_vault/core.py`

**Add Method 1: delete_organization()**

```python
async def delete_organization(
    self,
    org_id: UUID | str,
    force: bool = False,
) -> None:
    """
    Delete an organization.
    
    Args:
        org_id: Organization UUID
        force: If True, force delete even if organization has documents
        
    Raises:
        RuntimeError: If SDK not initialized
        OrganizationNotFoundError: If organization doesn't exist
        ValidationError: If organization has active documents and force=False
    """
    if not self._organization_service:
        raise RuntimeError("SDK not initialized. Use async context manager.")
    
    org_uuid = UUID(org_id) if isinstance(org_id, str) else org_id
    await self._organization_service.delete_organization(
        org_id=org_uuid,
        force=force,
    )
```

**Add Method 2: remove_agent()**

```python
async def remove_agent(
    self,
    agent_id: UUID | str,
    force: bool = False,
) -> None:
    """
    Remove an agent from the system.
    
    Args:
        agent_id: Agent UUID
        force: If True, force delete even if agent has created documents
        
    Raises:
        RuntimeError: If SDK not initialized
        AgentNotFoundError: If agent doesn't exist
        ValidationError: If agent has active documents and force=False
    """
    if not self._agent_service:
        raise RuntimeError("SDK not initialized. Use async context manager.")
    
    agent_uuid = UUID(agent_id) if isinstance(agent_id, str) else agent_id
    await self._agent_service.remove_agent(
        agent_id=agent_uuid,
        force=force,
    )
```

**Location**: Add after `register_agent()` method (around line 718)

**Verification**:
- [ ] Both methods added
- [ ] Proper error handling
- [ ] Docstrings complete
- [ ] Service methods called correctly

---

### Task 4: Fix Method Signatures (2-3 hours)

**Update 1: upload() - Add prefix parameter**

```python
async def upload(
    self,
    file_input: str | bytes | BinaryIO,  # Already flexible
    name: str,
    organization_id: str | UUID,
    agent_id: str | UUID,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    content_type: Optional[str] = None,
    filename: Optional[str] = None,
    prefix: Optional[str] = None,  # ADD THIS
) -> Document:
    """Upload a document with hierarchical organization support."""
    # Implementation needs to pass prefix to document service
```

**Update 2: list_docs() - Add hierarchical parameters**

```python
async def list_docs(
    self,
    organization_id: str | UUID,
    agent_id: str | UUID,
    prefix: Optional[str] = None,        # ADD THIS
    recursive: bool = False,             # ADD THIS
    max_depth: Optional[int] = None,     # ADD THIS
    status: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> Dict[str, Any]:
    """List documents with hierarchical prefix support."""
    # Implementation needs to use prefix/recursive parameters
```

**Update 3: get_permissions() - Add org_id parameter**

```python
async def get_permissions(
    self,
    document_id: str | UUID,
    agent_id: Optional[str | UUID] = None,
    org_id: str | UUID,                   # ADD THIS
) -> Dict[str, Any]:
    """Get permissions for a document."""
    # Implementation needs to validate org_id
```

**Update 4: search() - Already has prefix, verify**

```python
async def search(
    self,
    query: str,
    organization_id: str | UUID,
    agent_id: str | UUID,
    prefix: Optional[str] = None,  # Already present - verify
    status: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 20,
    offset: int = 0,
) -> Dict[str, Any]:
    """Search documents with optional prefix filtering."""
```

**Verification**:
- [ ] `upload()` has `prefix` parameter
- [ ] `list_docs()` has `prefix`, `recursive`, `max_depth`
- [ ] `get_permissions()` has `org_id` parameter
- [ ] All parameters properly documented
- [ ] Implementation updated to use new parameters

---

### Task 5: Handle Special Cases (1 hour)

**Decision Point: check_permissions_multi()**

This method was added in implementation but not in plan:

```python
async def check_permissions_multi(
    document_id: str | UUID,
    agent_id: str | UUID,
    permissions: List[str],
) -> Dict[str, Any]:
```

**Options**:
- **Option A**: Remove it (strict plan adherence)
- **Option B**: Keep it (useful utility)
- **Option C**: Fold into `get_permissions()` with parameter

**Recommendation**: Remove it. Users can call `get_permissions()` once and check multiple permissions locally.

**Decision Point: transfer_ownership()**

Not in original plan but useful:

```python
async def transfer_ownership(
    document_id: str | UUID,
    new_owner_id: str | UUID,
    transferred_by: str | UUID,
)
```

**Recommendation**: Keep it. Useful utility that doesn't conflict with plan.

**Verification**:
- [ ] Decision made on `check_permissions_multi()`
- [ ] Decision made on `transfer_ownership()`
- [ ] Actions taken accordingly

---

### Task 6: Update Internal Method Names (30 min)

**Update**: Old v1.x methods like `register_organization()` that use `external_id` parameter should be updated to use `org_id` or `agent_id` for consistency.

**Current**:
```python
async def register_organization(
    self,
    external_id: str,  # INCONSISTENT naming
    name: str = None,
    metadata: Optional[Dict[str, Any]] = None,
)
```

**Update to**:
```python
async def register_organization(
    self,
    org_id: UUID | str,  # CONSISTENT naming
    metadata: Optional[Dict[str, Any]] = None,
)
```

**Also update**: `register_agent()` to use `agent_id` instead of `external_id`

**Verification**:
- [ ] Parameter naming consistent across all methods
- [ ] No `external_id` parameters (use `org_id`, `agent_id`)
- [ ] Docstrings updated

---

## Testing Strategy

### Phase 1: Unit Tests (Day 3)

**Update Test Files**:
- `tests/test_core_v2.py` - Main v2.0 tests
- `tests/services/test_*.py` - Service layer tests (should still work)
- `tests/repositories/test_*.py` - Repository tests (should still work)

**Test Updates Required**:

1. **Remove tests for deleted methods**:
   - `test_share()`
   - `test_revoke()`
   - `test_check_permission()`
   - `test_list_accessible_documents()`
   - `test_get_document_permissions()`
   - `test_get_versions()`
   - `test_get_version_info()`

2. **Update method names in tests**:
   - `upload_enhanced()` → `upload()`
   - `list_documents_paginated()` → `list_docs()`
   - etc.

3. **Add tests for new methods**:
   - `test_delete_organization()`
   - `test_remove_agent()`

4. **Update test signatures**:
   - Add `prefix` parameter to `upload()` tests
   - Add `prefix`, `recursive`, `max_depth` to `list_docs()` tests
   - Add `org_id` to `get_permissions()` tests

**Verification**:
- [ ] All tests updated
- [ ] No references to old method names
- [ ] New method tests added
- [ ] Tests pass

---

### Phase 2: Integration Tests (Day 4)

**Run Full Test Suite**:
```bash
pytest tests/ -v --cov=doc_vault --cov-report=html
```

**Expected Results**:
- All tests pass
- Coverage > 80%
- No deprecated method calls

**Fix Issues**:
- Debug any test failures
- Update fixtures if needed
- Fix service layer integration if needed

**Verification**:
- [ ] Full test suite passes
- [ ] Coverage target met
- [ ] No warnings about missing methods

---

## Documentation Updates

### Task 7: Update Examples (Day 4)

**Files to Update**:
1. `examples/basic_usage_v2.py` ✅ (already done, but verify method names)
2. `examples/basic_usage.py` - Update to v2.0
3. `examples/access_control_v2.py` - Create v2.0 version
4. `examples/access_control.py` - Update to v2.0
5. `examples/versioning_v2.py` - Create v2.0 version
6. `examples/versioning.py` - Update to v2.0
7. `examples/multi_org.py` - Update to v2.0

**Changes Required**:
- Replace old method calls with v2.0 equivalents
- Update permission examples (`share()`/`revoke()` → `set_permissions()`)
- Update version examples (`get_versions()` → `get_document_details()`)
- Add hierarchical organization examples (prefix usage)

**Verification**:
- [ ] All examples updated
- [ ] Examples run successfully
- [ ] No old method calls

---

### Task 8: Update API.md (Day 4-5)

**Sections to Update**:

1. **Breaking Changes Section** (add at top):
   ```markdown
   ## Breaking Changes in v2.0
   
   See [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md) for complete migration instructions.
   
   ### Removed Methods
   - share() → Use set_permissions()
   - revoke() → Use set_permissions()
   - check_permission() → Use get_permissions()
   ...
   
   ### Renamed Methods
   - list_documents() → list_docs()
   - get_versions() → get_document_details(include_versions=True)
   ...
   ```

2. **Update All Method Documentation**:
   - Document new `upload()` with prefix
   - Document `list_docs()` with hierarchical parameters
   - Document `set_permissions()` and `get_permissions()`
   - Document `delete_organization()` and `remove_agent()`

3. **Add Migration Examples**:
   - v1.x code → v2.0 code side-by-side

**Verification**:
- [ ] Breaking changes documented
- [ ] All v2.0 methods documented
- [ ] Migration examples added
- [ ] No references to removed methods

---

### Task 9: Create MIGRATION_GUIDE.md (Day 5)

**Structure**:

```markdown
# Migration Guide: v1.x → v2.0

## Overview
DocVault v2.0 introduces breaking changes...

## Breaking Changes Summary

### Removed Methods
| v1.x Method | v2.0 Replacement |
|-------------|------------------|
| share() | set_permissions() |
...

### Renamed Methods
| v1.x Method | v2.0 Method |
|-------------|-------------|
| list_documents() | list_docs() |
...

### New Features
- Hierarchical document organization with prefix
- Bulk permission operations
- Organization/agent deletion

## Step-by-Step Migration

### 1. Update Permission Management
[Before/After code examples]

### 2. Update Document Listing
[Before/After code examples]

### 3. Update Version Management
[Before/After code examples]

## Common Migration Issues
...
```

**Verification**:
- [ ] Migration guide complete
- [ ] All breaking changes covered
- [ ] Code examples provided
- [ ] Common issues documented

---

## Timeline

### Day 1: Code Changes (6-8 hours)
- **Morning**: Tasks 1-2 (Remove & Rename methods)
- **Afternoon**: Tasks 3-4 (Add methods & Fix signatures)
- **Evening**: Task 5-6 (Special cases & naming)

### Day 2: Testing (6-8 hours)
- **Morning**: Update test files
- **Afternoon**: Run and debug tests
- **Evening**: Verify coverage

### Day 3: Documentation (6-8 hours)
- **Morning**: Update examples
- **Afternoon**: Update API.md
- **Evening**: Create MIGRATION_GUIDE.md

### Day 4: Validation & Polish (4-6 hours)
- **Morning**: Final test run
- **Afternoon**: Documentation review
- **Evening**: Commit and create PR

### Day 5: Buffer (optional)
- Address any issues found
- Additional testing
- Documentation polish

---

## Success Criteria

### Code
- [ ] 7 v1.x methods removed
- [ ] 6 methods renamed to match plan
- [ ] 2 new methods added
- [ ] All method signatures corrected
- [ ] File compiles without errors
- [ ] No breaking changes warnings

### Testing
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Coverage > 80%
- [ ] No deprecated method calls

### Documentation
- [ ] All examples updated and working
- [ ] API.md reflects v2.0
- [ ] MIGRATION_GUIDE.md complete
- [ ] Breaking changes clearly documented

### Release Readiness
- [ ] v2.0-checklist.md updated
- [ ] CHANGELOG.md updated
- [ ] Version bumped to 2.0.0
- [ ] Ready for Phase 12 (Release Preparation)

---

## Risk Mitigation

### Risk 1: Service Layer Integration Issues
**Mitigation**: Service layer already supports v2.0 (Phases 2-8 complete)

### Risk 2: Test Failures
**Mitigation**: Update tests incrementally, fix one at a time

### Risk 3: Documentation Drift
**Mitigation**: Update docs immediately after code changes

### Risk 4: User Impact
**Mitigation**: Clear migration guide, detailed breaking changes list

---

## Next Steps After Completion

1. Update v2.0-checklist.md - mark Phase 9 complete
2. Update Development Status memory
3. Proceed to Phase 12: Release Preparation
4. Create release branch
5. Final validation
6. PyPI release

---

**Status**: Ready to Begin  
**First Task**: Remove v1.x methods from core.py  
**Let's start! 🚀**
