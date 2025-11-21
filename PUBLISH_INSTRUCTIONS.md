# DocVault SDK v2.2.0 - Publishing Instructions

Complete guide for publishing DocVault SDK v2.2.0 to PyPI and GitHub.

**Release Date:** November 21, 2025  
**Version:** 2.2.0  
**Status:** ✅ Build Complete (ready for publishing)

---

## 📋 Pre-Publishing Checklist

✅ Completed Items:
- [x] Git repository cleaned (removed large file `examples/basic_usage_v2.py`)
- [x] Git tags created (`v2.2.0`)
- [x] Version number updated in `src/doc_vault/__init__.py` (2.2.0)
- [x] CHANGELOG.md updated with v2.2.0, v2.1.0, and v2.0.0 entries
- [x] Package built successfully (`uv build`)
- [x] Distribution files created:
  - `dist/docvault_sdk-2.2.0.tar.gz` (source distribution)
  - `dist/docvault_sdk-2.2.0-py3-none-any.whl` (wheel distribution)

---

## 🚀 Step 1: Publish to PyPI

### Prerequisites

1. **PyPI Account Required**
   - Create account at https://pypi.org/account/register/
   - Enable two-factor authentication (recommended)
   - Create API token at https://pypi.org/manage/account/tokens/

2. **Configure Authentication**

   **Option A: Using API Token (Recommended)**
   ```bash
   # Create ~/.pypirc file (Linux/Mac) or %APPDATA%\pip\pip.ini (Windows)
   [distutils]
   index-servers = pypi

   [pypi]
   repository = https://upload.pypi.org/legacy/
   username = __token__
   password = pypi-AgEIcHlwaS5vcmc...  # Your API token here
   ```

   **Option B: Using Username/Password (Less Secure)**
   ```bash
   [distutils]
   index-servers = pypi

   [pypi]
   repository = https://upload.pypi.org/legacy/
   username = your_username
   password = your_password
   ```

3. **Install Twine (Python Package Uploader)**
   ```bash
   pip install twine
   # or
   uv pip install twine
   ```

### Publishing Steps

```bash
# Navigate to project directory
cd z:\code\doc_vault

# Verify build artifacts exist
ls dist/  # Should show:
#   docvault_sdk-2.2.0.tar.gz
#   docvault_sdk-2.2.0-py3-none-any.whl

# (Optional) Test upload to PyPI test server first
twine upload --repository testpypi dist/*

# Upload to PyPI production (LIVE - cannot be undone!)
twine upload dist/*

# You should see output like:
# Uploading distributions to https://upload.pypi.org/legacy/
# Uploading docvault_sdk-2.2.0.tar.gz
# Uploading docvault_sdk-2.2.0-py3-none-any.whl
# Uploaded docvault_sdk to PyPI
```

### Verify PyPI Publication

After upload (may take 1-2 minutes to appear):
1. Visit https://pypi.org/project/docvault-sdk/
2. Verify v2.2.0 is listed as latest version
3. Check release notes display correctly
4. Test installation: `pip install --upgrade docvault-sdk==2.2.0`

---

## 📦 Step 2: Publish to GitHub Releases

### Create GitHub Release via Web UI (Recommended)

1. **Navigate to GitHub Releases**
   - Go to: https://github.com/Ganzzi/doc-vault/releases
   - Click "Create a new release"

2. **Fill in Release Details**

   **Tag Version:** `v2.2.0`
   
   **Release Title:** `v2.2.0: Type Safety & Response Models Release`
   
   **Release Notes:** (See section below for complete text)

3. **Attach Build Artifacts**
   - Drag and drop or select files:
     - `dist/docvault_sdk-2.2.0.tar.gz`
     - `dist/docvault_sdk-2.2.0-py3-none-any.whl`

4. **Publish Release**
   - ✅ Check "Set as the latest release"
   - Click "Publish release"

### Create GitHub Release via CLI

```bash
# Install GitHub CLI (if not already installed)
# https://cli.github.com/

# Create release with auto-generated changelog
gh release create v2.2.0 \
  --repo Ganzzi/doc-vault \
  --title "v2.2.0: Type Safety & Response Models Release" \
  --notes-file RELEASE_NOTES_v2.2.0.md \
  dist/docvault_sdk-2.2.0.tar.gz \
  dist/docvault_sdk-2.2.0-py3-none-any.whl
```

---

## 📝 Release Notes Content

Copy this content for GitHub release notes:

```markdown
# v2.2.0: Type Safety & Response Models Release

**Combined Release of v2.0, v2.1, and v2.2 Features**

This release bundles three major versions (v2.0.0, v2.1.0, and v2.2.0) into a single v2.2.0 release, providing the complete modern DocVault SDK with enterprise-grade features.

## 🎯 What's New in v2.2 (Type Safety & Response Models)

### Type-Safe Response Models
- All methods now return explicit Pydantic response models instead of generic dictionaries
- Full IDE autocomplete and type checking support
- Response models:
  - `DocumentListResponse` - for list_docs()
  - `SearchResponse` - for search()
  - `DocumentDetails` - for get_document_details()
  - `PermissionListResponse` - for get_permissions()
  - `OwnershipTransferResponse` - for transfer_ownership()
  - `PaginationMeta` - consistent pagination across operations

### Smart String Upload Detection
- Automatic detection of file paths vs. text content in `upload()`
- No temporary files needed for text uploads
- Supports UTF-8 encoding with automatic filename defaults
- Example:
  ```python
  # Automatically detected as text (no temp file!)
  doc = await vault.upload(
      file_input="This is my document content",
      name="Document",
      organization_id=org_id,
      agent_id=agent_id
  )
  ```

### Enhanced SDK
- All methods accept `str | UUID` for ID parameters
- Consistent UUID handling throughout
- Simplified internal parameter processing
- Removed v1.x compatibility helpers

## 🔧 What's New in v2.1 (Security & Type Safety Polish)

### Security Improvements
- **Permission viewing restricted to document owners only** - prevents information leakage
- Comprehensive error documentation for all methods (17 SDK methods)
- Security-focused API design

### Type-Safe Permissions
- New `PermissionGrant` Pydantic model
- Automatic field validation
- Full IDE autocomplete support
- Backward compatible with dict format

### API Improvements
- Removed unused parameters for cleaner API
- Better error messages with clear context
- Comprehensive docstring documentation

## 🚀 What's New in v2.0 (Major Architecture Overhaul)

### UUID-Based Entity Model
- Organizations and Agents now use external UUIDs as primary identifiers
- Pure reference entity model enables integration with external systems
- Removed internal duplication and simplified design

### Hierarchical Document Organization
- Document prefix-based hierarchy support (S3-like structure)
- Example: `/reports/2025/q1/financial.pdf`
- Backward compatible (prefix is optional)
- Recursive listing with depth control

### Enhanced Permissions API
- `get_permissions()` - retrieve all permissions for a document
- `set_permissions()` - bulk permission updates
- Role-based permissions: READ, WRITE, DELETE, SHARE, ADMIN
- Permission expiration and metadata support

### Service Layer
- `OrganizationService` - organization lifecycle management
- `AgentService` - agent management
- `AccessService` - unified permissions API
- `DocumentService` - hierarchical document operations
- Cascade delete operations with safety checks

### Comprehensive Testing
- 60+ tests validating type safety (v2.2)
- 100+ integration tests (v2.0/v2.1)
- mypy type checking validation
- 44% code coverage

## ✨ Key Features Across All Versions

### Document Management
- ✅ Upload, download, update metadata, delete documents
- ✅ Support for multiple input types: file paths, bytes, binary streams
- ✅ Hierarchical document organization with prefix-based structure
- ✅ Automatic versioning on content replacement

### Access Control
- ✅ Role-based permissions (READ, WRITE, DELETE, SHARE, ADMIN)
- ✅ Granular ACL for fine-grained access
- ✅ Permission expiration and metadata
- ✅ Bulk permission updates

### Version Management
- ✅ Document versioning with history
- ✅ Version restore functionality
- ✅ Version metadata and change descriptions
- ✅ Automatic version tracking

### Multi-Organization Support
- ✅ Strong isolation between organizations
- ✅ Agent management per organization
- ✅ Cascade delete operations
- ✅ UUID-based external identity integration

### Advanced Features
- ✅ Full-text search with PostgreSQL tsvector
- ✅ Async-first design with proper resource management
- ✅ Type-safe API with mypy support
- ✅ Pydantic data validation
- ✅ S3/MinIO compatible storage

## 📦 Installation

```bash
# Install latest version
pip install --upgrade docvault-sdk

# Or install specific version
pip install docvault-sdk==2.2.0

# With optional dependencies
pip install docvault-sdk[dev]  # Includes development tools
```

## 🔄 Migration Guide

**From v2.1 to v2.2:**
- Update response handling to use attributes instead of dictionary keys
- Update type hints for response variables
- No other changes needed

**From v2.0 to v2.1:**
- Remove `org_id` parameter from `get_permissions()` and `set_permissions()`
- Optionally migrate to `PermissionGrant` model for type safety
- Handle `PermissionDeniedError` when viewing permissions as non-owner

**From v1.x to v2.x:**
- Complete API overhaul - see migration guide
- Database schema changes require migration script
- UUID-based identities instead of strings

See [MIGRATION_v2.1_to_v2.2.md](docs/MIGRATION_v2.1_to_v2.2.md) and [MIGRATION_v2.0_to_v2.1.md](docs/MIGRATION_v2.0_to_v2.1.md) for detailed migration instructions.

## 🧪 Testing & Quality

- ✅ 60+ type safety tests (v2.2)
- ✅ 100+ integration tests (v2.0/v2.1)
- ✅ mypy type checking (all clean)
- ✅ 44% code coverage
- ✅ All tests passing

## 📚 Documentation

- **API Documentation:** [docs/API.md](docs/API.md)
- **Test Strategy:** [docs/TEST_STRATEGY.md](docs/TEST_STRATEGY.md)
- **Migration Guides:** [docs/MIGRATION_*.md](docs/)
- **Examples:** [examples/](examples/)

## 🐛 Bug Fixes

- Fixed: Permission viewing security gap (v2.1)
- Fixed: Type safety gaps in public API (v2.2)
- Fixed: String upload behavior now matches documentation (v2.2)
- Fixed: Large file support with hierarchical paths (v2.0)

## 🙏 Contributors

- DocVault Development Team

## 📄 License

MIT License - See [LICENSE](LICENSE) file

---

**For detailed changelog, see [CHANGELOG.md](CHANGELOG.md)**
```

---

## ⚡ Quick Commands Reference

### If You Need to Undo

```bash
# If you just uploaded and want to delete the release (within minutes)
# PyPI doesn't allow deletion, but you can upload a newer version

# For GitHub release (if not yet published):
# Just don't publish - draft releases can be deleted

# To unpublish from PyPI (if critical issue):
# Contact PyPI admins or release a patch version (2.2.1)
```

### Verify Installation

```bash
# Test in fresh Python environment
pip install docvault-sdk==2.2.0

# Verify version
python -c "import doc_vault; print(doc_vault.__version__)"
# Should output: 2.2.0

# Test import
python -c "from doc_vault import DocVaultSDK; print('✅ Import successful')"
```

---

## 📊 Release Summary

| Aspect | v2.0.0 | v2.1.0 | v2.2.0 | Combined |
|--------|--------|--------|--------|----------|
| **Release Type** | Major (Architecture Overhaul) | Refinement (Security & Polish) | Enhancement (Type Safety) | **Complete SDK** |
| **Response Types** | Dict[str, Any] | Dict[str, Any] | Pydantic Models | ✅ Type-Safe |
| **Permissions** | Basic RBAC | Security Enhanced | Full Type-Safe | ✅ Secure & Typed |
| **Tests** | ~100 integration | +4 security | +60 type-safety | **160+ tests** |
| **Breaking Changes** | 7 major API changes | 2 minor removals | Response type changes | Well-documented |

---

## 🎯 Next Steps

1. ✅ Build artifacts ready: `dist/docvault_sdk-2.2.0.*`
2. 📤 Publish to PyPI (use `twine upload`)
3. 🏷️ Create GitHub release (attach artifacts)
4. 🔗 Update documentation links
5. 📢 Announce on social media/community forums

---

**Generated:** November 21, 2025  
**Status:** Ready for Publishing ✅
