# Changelog

All notable changes to DocVault SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2025-11-21

**v2.1 Refinement Release** - Security, Type Safety, and API Polish

This release focuses on addressing technical debt and improving API consistency discovered after the v2.0.0 release. No new features were added, but significant improvements to security, type safety, and developer experience make this a recommended upgrade for all v2.0 users.

### Added

- **Type-Safe Permissions** 🎯
  - New `PermissionGrant` Pydantic model for type-safe permission operations
  - Automatic field validation for permission levels (READ, WRITE, DELETE, SHARE, ADMIN)
  - UUID format validation for agent_id fields
  - Full IDE autocomplete and type hints support
  - Backward compatible with dict format
  
- **Comprehensive Documentation** 📝
  - Added `Raises` sections to all SDK method docstrings (17 methods updated)
  - Created 540-line docstring template guide with best practices
  - Documented all possible exceptions for each method
  - Added security notes in API documentation
  - Enhanced examples with v2.1 patterns

- **Enhanced Security** 🔒
  - Permission viewing now restricted to document owners (ADMIN permission)
  - Non-owners receive `PermissionDeniedError` when attempting to view permissions
  - Prevents information leakage about document access
  - Service layer enforces ownership checks before returning permissions

### Changed - API Improvements (Minor Breaking)

- **`get_permissions()` signature simplified:**
  - ❌ Removed unused `org_id` parameter (permissions are document-scoped, not org-scoped)
  - ✅ Cleaner API: `get_permissions(document_id, agent_id=None)` 
  - Returns dictionary with metadata instead of plain list
  - More focused and intuitive interface

- **`set_permissions()` enhanced with type safety:**
  - 🎯 Now accepts `List[PermissionGrant]` (typed model) instead of `List[dict]`
  - ✅ Automatic validation through Pydantic
  - 🔄 Backward compatible: Still accepts `List[dict]` format
  - ❌ Removed unused `org_id` parameter
  - Returns `List[DocumentACL]` instead of `None`

- **`get_document_details()` security enhancement:**
  - 🔒 `include_permissions=True` now requires ADMIN permission
  - ✅ Prevents non-owners from viewing document permissions
  - Clear error message when non-owner attempts to view permissions
  - No changes for `include_versions` - still accessible to any READ-permission holder

### Security

- **Permission Viewing Restriction** (BREAKING for some use cases)
  - Only document owners (ADMIN permission) can view who has access
  - Non-owners calling `get_document_details(include_permissions=True)` now get `PermissionDeniedError`
  - Prevents information leakage about document sharing
  - **Migration:** Update code to check ADMIN permission before viewing permissions

### Fixed

- **API Consistency Issues:**
  - Removed unused `org_id` parameter from `get_permissions()` (was accepted but never used)
  - Fixed misleading parameter that suggested org-level permission filtering
  
- **Type Safety Gaps:**
  - Using plain dicts for permissions now has typed alternative
  - Better validation catches errors at API call time instead of runtime
  
- **Documentation Gaps:**
  - All methods now document exceptions they can raise
  - Users know what to catch without reading source code
  - Clear security requirements documented

### Developer Experience Improvements

- **IDE Support:**
  - Full autocomplete for `PermissionGrant` model fields
  - Type hints help catch errors before runtime
  - Better documentation tooltips in IDEs
  
- **Error Messages:**
  - Clear security errors: "Only document owners (ADMIN permission) can view permissions"
  - Validation errors show exactly what's wrong (e.g., "Permission must be one of [READ, WRITE, DELETE, SHARE, ADMIN]")
  
- **API Clarity:**
  - Removed confusing unused parameters
  - Consistent parameter naming
  - Better docstring examples

### Migration from v2.0 to v2.1

**Breaking Changes (Minor):**

1. **`get_permissions()` - Remove `org_id` parameter:**
```python
# v2.0
perms = await vault.get_permissions(
    document_id=doc_id,
    agent_id=agent_id,
    org_id=org_id  # ❌ Remove this
)

# v2.1
perms = await vault.get_permissions(
    document_id=doc_id,
    agent_id=agent_id  # ✅ org_id removed
)
```

2. **`set_permissions()` - Remove `org_id`, optionally use PermissionGrant:**
```python
# v2.0
await vault.set_permissions(
    document_id=doc_id,
    org_id=org_id,  # ❌ Remove this
    permissions=[{"agent_id": agent_id, "permission": "READ"}],
    granted_by=admin_id
)

# v2.1 (backward compatible)
await vault.set_permissions(
    document_id=doc_id,
    permissions=[{"agent_id": agent_id, "permission": "READ"}],
    granted_by=admin_id
)

# v2.1 (recommended - type safe)
from doc_vault.database.schemas.permission import PermissionGrant

await vault.set_permissions(
    document_id=doc_id,
    permissions=[
        PermissionGrant(agent_id=agent_id, permission="READ")
    ],
    granted_by=admin_id
)
```

3. **`get_document_details()` - Permission viewing restricted:**
```python
# v2.0 - any agent could view permissions
details = await vault.get_document_details(
    document_id=doc_id,
    agent_id=any_agent_id,  # ⚠️ Could be non-owner
    include_permissions=True  # Would succeed
)

# v2.1 - only ADMIN can view permissions
try:
    details = await vault.get_document_details(
        document_id=doc_id,
        agent_id=non_owner_id,
        include_permissions=True  # ❌ Raises PermissionDeniedError
    )
except PermissionDeniedError:
    print("Only document owners can view permissions")

# Only owners (ADMIN permission) can view permissions
details = await vault.get_document_details(
    document_id=doc_id,
    agent_id=owner_id,  # ✅ Must have ADMIN permission
    include_permissions=True
)
```

**Recommended Actions:**
1. Update all `get_permissions()` calls to remove `org_id` parameter
2. Update all `set_permissions()` calls to remove `org_id` parameter
3. Optionally migrate to `PermissionGrant` model for better type safety
4. Review code that calls `get_document_details(include_permissions=True)` and ensure it handles `PermissionDeniedError` or only calls with ADMIN agents
5. Update tests to reflect security changes

**Non-Breaking Changes:**
- All docstrings now include `Raises` sections (informational only)
- `set_permissions()` returns `List[DocumentACL]` instead of `None` (additive change)
- `get_permissions()` returns dict with metadata (structure change but backward compatible)

### Technical Details

**Files Modified:**
- `src/doc_vault/core.py`: Updated 17 method docstrings with comprehensive `Raises` sections
- `src/doc_vault/services/document_service.py`: Added ADMIN permission check for permission viewing
- `src/doc_vault/database/schemas/permission.py`: NEW - `PermissionGrant` model (89 lines)
- `src/doc_vault/database/schemas/__init__.py`: Export `PermissionGrant`
- `tests/test_core_permissions.py`: NEW - 4 comprehensive security tests (180 lines)
- `tests/conftest.py`: Added test fixtures for permission tests
- `docs/docstring_template.md`: NEW - Complete documentation guide (540 lines)
- `docs/API.md`: Updated with v2.1 changes and security notes

**Code Quality:**
- ~1,100 lines of new/modified code
- All changes maintain backward compatibility except documented breaking changes
- Enhanced type safety through Pydantic models
- Improved security posture
- Better developer experience

**Testing:**
- All existing tests pass
- 4 new security tests for permission viewing restrictions
- Test fixtures updated to support v2.1 changes
- Examples validated with v2.1 API

### Upgrade Recommendation

**Recommended for all v2.0 users.** The security enhancement (permission viewing restriction) may require code changes if you're calling `get_document_details(include_permissions=True)` with non-owner agents. The API parameter removals are straightforward to fix.

**Estimated migration time:** 15-30 minutes for typical applications

See [docs/MIGRATION_v2.0_to_v2.1.md](docs/MIGRATION_v2.0_to_v2.1.md) for detailed migration guide.

---

## [2.0.0] - 2025-11-20

### Added - Major Architecture Overhaul
- **UUID-Based Entity Model**: Organizations and Agents now use external UUIDs as primary identifiers
  - Removed internal external_id duplication
  - Organizations no longer store name/metadata
  - Agents no longer store name/email/agent_type
  - Pure reference entity model enables integration with external systems
  
- **Hierarchical Document Organization**: New prefix-based document hierarchy support
  - Documents support prefix/path columns for S3-like organization
  - Example structure: `/reports/2025/q1/financial.pdf`
  - Backward compatible (prefix is optional)
  - New path validation and utilities
  
- **Enhanced Document Listing**:
  - `list_documents_by_prefix()`: List documents under a prefix
  - `list_documents_recursive()`: Recursive listing with depth control
  - Depth-aware hierarchy traversal
  - Permission-filtered results
  
- **Flexible Upload System**:
  - Support multiple input types: file paths (str), bytes, binary streams (BinaryIO)
  - Automatic hierarchical path generation from prefix + name
  - StreaminG support for large files
  
- **Unified Permissions API**:
  - `get_permissions()`: Retrieve all permissions for a document
  - `set_permissions()`: Bulk permission updates in atomic operation
  - Consolidated from multiple grant/revoke/check methods
  - Support for permission expiration and metadata
  
- **New Service Layer**:
  - `OrganizationService`: Organization lifecycle management with cascade delete
  - `AgentService`: Agent management with organization operations
  - `AccessService`: Enhanced with v2.0 unified permissions API
  - `DocumentService`: Updated with hierarchical operations
  - All services include comprehensive error handling and logging
  
- **Cascade Delete Operations**:
  - Organization deletion can cascade delete agents and documents
  - Agent removal can cascade delete documents and ACLs
  - Force parameter for safe cascade operations
  - Detailed error messages when cascade would affect data
  
- **Comprehensive Test Suite**:
  - 1,300+ lines of unit tests across 5 test modules
  - 32 test classes covering all repository and service operations
  - Tests for cascade delete, permissions, hierarchical operations
  - Test infrastructure for all v2.0 features

### Changed - Breaking Changes
- **Database Schema**:
  - Organizations table: Removed external_id, name columns
  - Agents table: Removed external_id, name, email, agent_type columns
  - Documents table: Added prefix and path columns with indexes
  - Migration script provided for v1 → v2 upgrade
  
- **API Signatures** (Breaking):
  - `register_organization()`: Now accepts id: UUID (required), no name parameter
  - `register_agent()`: Now accepts id: UUID (required), no name/email/agent_type parameters
  - `upload()`: Now accepts file_path: Union[str, bytes, BinaryIO]
  - `list_documents()` → `list_docs()`: New method with prefix/recursive/max_depth parameters
  - Removed methods: share(), revoke(), check_permission(), list_accessible_documents(), get_document_permissions(), get_version_info(), get_versions()
  - Added methods: delete_organization(), remove_agent(), get_permissions(), set_permissions(), list_docs(), get_document_details()

### Removed - v1 Methods
- `share()`: Use `set_permissions()` instead
- `revoke()`: Use `set_permissions()` instead
- `check_permission()`: Use `get_permissions()` instead
- `list_accessible_documents()`: Use `list_docs()` instead
- `get_document_permissions()`: Use `get_permissions()` instead
- `get_version_info()`: Use `get_document_details(include_versions=True)` instead
- `get_versions()`: Use `get_document_details(include_versions=True)` instead

### Migration Notes
- Database migration from v1 to v2 requires running migration script
- All API calls must be updated due to breaking changes
- See MIGRATION_V1_TO_V2.md for detailed upgrade instructions
- External ID values are migrated to organization/agent UUIDs
- No data loss during migration if done correctly

## [1.0.0] - 2025-10-16

### Added
- **Complete SDK Implementation**: Full DocVault SDK with document management, access control, and versioning
- **Document Operations**: Upload, download, update metadata, replace content, delete documents
- **Access Control**: Role-based permissions (READ, WRITE, DELETE, SHARE, ADMIN) with granular ACL
- **Version Management**: Document versioning with restore functionality
- **Multi-Organization Support**: Strong isolation between organizations with bucket-per-org architecture
- **PostgreSQL Integration**: Full database layer with psqlpy async driver
- **MinIO/S3 Storage**: Binary file storage with presigned URLs
- **Comprehensive API**: Clean async API with context manager support
- **Extensive Testing**: 66%+ test coverage with integration tests
- **CI/CD Pipeline**: GitHub Actions with multi-Python version testing
- **Docker Support**: Complete docker-compose setup for local development
- **Documentation**: Complete README, API docs, examples, and development guide

### Technical Features
- **Async-First Design**: All operations are async with proper resource management
- **Type Safety**: Full Pydantic models with mypy support
- **Repository Pattern**: Clean data access layer with base repository
- **Service Layer**: Business logic orchestration with proper error handling
- **Storage Abstraction**: S3-compatible storage backend interface
- **Database Triggers**: Auto-updating timestamps and search vectors
- **Full-Text Search**: PostgreSQL tsvector support for document search
- **Foreign Key Constraints**: Data integrity with proper relationships

### Dependencies
- psqlpy: High-performance async PostgreSQL driver
- pydantic v2: Data validation and settings
- minio: S3-compatible object storage client
- PostgreSQL 14+: Metadata storage with pgvector support
- MinIO/S3: Binary file storage

### Breaking Changes
- Initial release - no breaking changes from previous versions

### Known Limitations
- PDF processing features planned for v2.0
- Semantic search requires pgvector extension (available in docker-compose)
- Bulk operations not yet implemented

### Contributors
- DocVault Development Team

---

## [0.1.0] - 2025-10-15

### Added
- Initial project setup and configuration
- Basic project structure with all directories
- Dependency management with uv/poetry
- Initial database schema design
- Basic exception hierarchy
- Configuration management layer

### Infrastructure
- Project scaffolding
- Git repository initialization
- Basic CI/CD setup
- Development environment configuration

---

The DocVault SDK v1.0.0 represents a complete, production-ready document management solution for organizations and AI agents. The SDK provides enterprise-grade features including role-based access control, document versioning, and multi-organization isolation.

For installation and usage instructions, see the [README.md](README.md).