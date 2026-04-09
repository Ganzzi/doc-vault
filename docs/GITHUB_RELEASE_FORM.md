# GitHub Release Form - v2.2.0

**Complete data for creating GitHub Release**

---

## Release Form Fields

### 📌 Tag Version
```
v2.2.0
```

### 📋 Release Title
```
v2.2.0: Type Safety & Response Models Release
```

### ✅ Set as Latest Release
```
Check this box (enabled by default)
```

### 📝 Release Notes/Description

**Copy and paste the following text into the "Description" field:**

---

```markdown
# v2.2.0: Type Safety & Response Models Release

**Combined Release of v2.0, v2.1, and v2.2 Features**

This release bundles three major versions (v2.0.0, v2.1.0, and v2.2.0) into a single v2.2.0 release, providing the complete modern DocVault SDK with enterprise-grade features.

## 🎯 v2.2 - Type Safety & Response Models

### Type-Safe Response Models ✨
All methods now return explicit Pydantic response models instead of generic dictionaries:
- **DocumentListResponse** - for `list_docs()` with pagination
- **SearchResponse** - for `search()` with query metadata
- **DocumentDetails** - for `get_document_details()` with versions and permissions
- **PermissionListResponse** - for `get_permissions()` with metadata
- **OwnershipTransferResponse** - for `transfer_ownership()` with all details
- **PaginationMeta** - consistent pagination across all list/search operations

**Benefits:**
- ✅ Full IDE autocomplete on all response fields
- ✅ Type checking catches errors at development time
- ✅ Self-documenting response structures
- ✅ Mypy validation passes cleanly

### Smart String Upload Detection 🧠
Automatic detection of file paths vs. text content:
```python
# No temporary files needed!
doc = await vault.upload(
    file_input="This is my document content",
    name="My Document",
    organization_id=org_id,
    agent_id=agent_id
)
```

**Features:**
- File path detection: `Path(file_input).exists()` → reads file
- Text content: Non-existent paths → treats as raw text
- UTF-8 encoding with automatic filename defaults
- Supports empty strings, Unicode, large text, Windows paths

### Enhanced SDK 🚀
- All ID methods accept `str | UUID` (not just strings)
- Consistent UUID handling throughout codebase
- Simplified internal parameter processing
- Removed v1.x compatibility helpers (`_resolve_external_ids`)

### Type Safety Improvements
- Zero `Dict[str, Any]` in public API
- Zero `List[Any]` in public API
- All return types are explicit and documented
- Full mypy validation passes

---

## 🔧 v2.1 - Security & Type Safety Polish

### Security Enhancements 🔒
- **Permission viewing restricted to document owners only**
  - Prevents information leakage about document access
  - Non-owners receive `PermissionDeniedError` when requesting permissions
  - Service layer enforces ownership checks
  
### Type-Safe Permissions Model 🎯
- New `PermissionGrant` Pydantic model for type-safe operations
- Automatic field validation for permission levels
- UUID format validation for agent_id
- Backward compatible with dict format

### API Improvements 📝
- Removed unused `org_id` parameter from `get_permissions()` and `set_permissions()`
- Enhanced error messages with clear security context
- Comprehensive `Raises` sections in all 17 SDK method docstrings

### Developer Experience
- Full IDE support with type hints and autocomplete
- Better error messages explaining what went wrong
- Clear security requirements in documentation
- Self-documenting code through types

---

## 🚀 v2.0 - Major Architecture Overhaul

### UUID-Based Entity Model 🆔
- Organizations and Agents now use external UUIDs as primary identifiers
- Pure reference entity model for external system integration
- Eliminated internal ID duplication
- Simplified database schema

### Hierarchical Document Organization 📁
- Document prefix-based hierarchy support (S3-like structure)
- Example: `/reports/2025/q1/financial.pdf`
- Recursive listing with depth control
- Backward compatible (prefix optional)

### Enhanced Permissions API 🔐
- `get_permissions()` - retrieve all permissions for a document
- `set_permissions()` - bulk permission updates in atomic operation
- Role-based permissions: READ, WRITE, DELETE, SHARE, ADMIN
- Permission expiration and metadata support

### Service Layer Architecture 🏗️
- **OrganizationService** - organization lifecycle with cascade delete
- **AgentService** - agent management with organization operations
- **AccessService** - unified permissions API with security checks
- **DocumentService** - hierarchical operations and versioning
- Comprehensive error handling and logging

### Cascade Delete Operations ⚠️
- Organization deletion can cascade delete agents and documents
- Agent removal can cascade delete documents and ACLs
- Safe force parameters with detailed error messages
- No data loss if done correctly

---

## ✨ Complete Feature Set

### Document Management
- ✅ Upload, download, update metadata, delete documents
- ✅ Multiple input types: file paths, bytes, binary streams
- ✅ Hierarchical prefix-based organization
- ✅ Automatic versioning on content replacement
- ✅ Full-text search with PostgreSQL

### Access Control
- ✅ Role-based permissions (READ, WRITE, DELETE, SHARE, ADMIN)
- ✅ Granular ACL for fine-grained control
- ✅ Permission expiration and metadata
- ✅ Bulk permission updates
- ✅ Security-first design (owner-only permission viewing)

### Version Management
- ✅ Document versioning with full history
- ✅ Version restore functionality
- ✅ Version metadata and change descriptions
- ✅ Automatic version tracking

### Multi-Organization Support
- ✅ Strong organization isolation
- ✅ Per-organization agent management
- ✅ UUID-based external identity mapping
- ✅ Cascade delete with safety checks

### Technical Excellence
- ✅ Async-first design with proper resource management
- ✅ Type-safe API (Pydantic + mypy validation)
- ✅ S3/MinIO compatible storage backend
- ✅ PostgreSQL with advanced features (tsvector, JSON)
- ✅ Clean repository pattern architecture

---

## 📊 Testing & Quality

| Metric | Result |
|--------|--------|
| **Response Model Tests** | ✅ 19 tests passing |
| **Upload Detection Tests** | ✅ 14 tests passing |
| **Integration Tests** | ✅ 27+ tests passing |
| **Total Test Suite** | ✅ 60+ tests passing |
| **Type Checking** | ✅ mypy clean |
| **Code Coverage** | ✅ 44% (integration test level) |
| **Response Model Coverage** | ✅ 100% |

---

## 🔄 Migration Paths

### v2.1 → v2.2 (Type Safety)
```python
# v2.1 - Dictionary access
result = await vault.list_docs(org_id=org_id, agent_id=agent_id)
docs = result["documents"]

# v2.2 - Attribute access (recommended)
result = await vault.list_docs(org_id=org_id, agent_id=agent_id)
docs = result.documents  # Type-safe!
```

**Effort:** ~30-45 minutes for typical applications

### v2.0 → v2.1 (Security)
```python
# v2.0 - Any agent could view permissions
details = await vault.get_document_details(
    document_id=doc_id,
    agent_id=any_agent_id,
    include_permissions=True  # ⚠️ Security issue
)

# v2.1 - Only ADMIN permission holders
details = await vault.get_document_details(
    document_id=doc_id,
    agent_id=admin_agent_id,  # Must have ADMIN permission
    include_permissions=True  # ✅ Secure
)
```

**Effort:** ~15-30 minutes for typical applications

### v1.x → v2.x (Complete Overhaul)
**Major breaking changes - complete API migration needed**

See [MIGRATION_v2.1_to_v2.2.md](docs/MIGRATION_v2.1_to_v2.2.md) and [MIGRATION_v2.0_to_v2.1.md](docs/MIGRATION_v2.0_to_v2.1.md) for detailed migration instructions.

---

## 📦 Installation

```bash
# Install latest version
pip install --upgrade docvault-sdk

# Or install specific version
pip install docvault-sdk==2.2.0

# With optional development dependencies
pip install docvault-sdk[dev]
```

---

## 🐛 Bug Fixes & Improvements

### Fixed in v2.2
- ✅ Type safety gaps in public API (all Dict[str, Any] removed)
- ✅ String upload behavior now matches documentation
- ✅ UUID parameter handling consistent across all methods
- ✅ Service layer response model returns (transfer_ownership)

### Fixed in v2.1
- ✅ Permission viewing security gap (owner-only access)
- ✅ Unused parameters removed (cleaner API)
- ✅ Documentation gaps (Raises sections added)
- ✅ Type safety for permissions

### Fixed in v2.0
- ✅ Entity model simplified (UUID-based, no duplication)
- ✅ Large file support (hierarchical paths)
- ✅ Permissions API unified (get + set methods)
- ✅ Cascade delete safety

---

## 📚 Documentation

- **Getting Started:** [README.md](README.md)
- **API Reference:** [docs/API.md](docs/API.md)
- **Test Strategy:** [docs/TEST_STRATEGY.md](docs/TEST_STRATEGY.md)
- **Migration Guides:** [docs/MIGRATION_*.md](docs/)
- **Examples:** [examples/](examples/)
- **Changelog:** [CHANGELOG.md](CHANGELOG.md)

---

## 🎯 Recommended Actions

1. **Update to v2.2.0** - Recommended for all users
   - Estimated migration time: 30-45 minutes
   - Comprehensive type safety improvements
   - Smart upload detection (no more temp files)

2. **Review Security Changes** - If upgrading from v2.0
   - Permission viewing now restricted to owners
   - May require code changes if viewing permissions from non-owners
   - Clear error messages guide necessary changes

3. **Leverage Type Safety** - Start using new response models
   - Full IDE autocomplete on all response fields
   - Type checking catches errors before runtime
   - Better documentation through types

---

## 🙏 Contributors

- DocVault Development Team

## 📄 License

MIT License - See [LICENSE](LICENSE) file

---

**Release Date:** November 21, 2025  
**Build:** Successful ✅  
**Status:** Production Ready 🚀
```

---

## 📎 Attachments (Files to Upload)

In GitHub release form, upload these files:

1. **dist/docvault_sdk-2.2.0.tar.gz**
   - Source distribution
   - Contains all source code
   - Install with: `pip install docvault_sdk-2.2.0.tar.gz`

2. **dist/docvault_sdk-2.2.0-py3-none-any.whl**
   - Wheel distribution (pre-built)
   - Faster installation
   - Install with: `pip install docvault_sdk-2.2.0-py3-none-any.whl`

---

## ✅ Publishing Checklist

Before clicking "Publish release":

- [ ] Tag version is correct: `v2.2.0`
- [ ] Release title is set: `v2.2.0: Type Safety & Response Models Release`
- [ ] Release notes are complete (use text above)
- [ ] Both distribution files are attached
- [ ] "Set as the latest release" is checked
- [ ] Description mentions all three versions (v2.0, v2.1, v2.2)
- [ ] Links to migration guides are included
- [ ] Installation instructions are clear

---

## 🔗 Quick Links

- **PyPI Package:** https://pypi.org/project/docvault-sdk/
- **GitHub Repository:** https://github.com/Ganzzi/doc-vault
- **Documentation:** https://github.com/Ganzzi/doc-vault/blob/main/README.md
- **Issue Tracker:** https://github.com/Ganzzi/doc-vault/issues

---

**Generated:** November 21, 2025  
**Ready for Publication:** ✅ YES
