HANGELOG.md</path>
<content lines="1-50">
# Changelog

All notable changes to DocVault SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **Configuration System Refactoring**: Simplified config from nested classes to flat structure
  - Flattened PostgresConfig, MinioConfig, DocVaultConfig into single Config class
  - Clear field naming with prefixes (postgres_*, minio_*)
  - Support for three configuration patterns:
    * Direct Python Configuration (recommended for PyPI users)
    * Environment Variables (recommended for Docker/Kubernetes)
    * .env File Configuration (convenient for local development)
- **Dependency Management**: Moved python-dotenv to optional dev dependencies
  - Production installations no longer require python-dotenv
  - .env file support still available for local development
- **Documentation**: Complete rewrite of Configuration section in README
  - Added comprehensive examples for all three configuration patterns
  - Added Configuration Priority and Reference tables

### Removed
- Unused environment variables: DEBUG, MINIO_REGION, MINIO_PORT, MINIO_CONSOLE_PORT
- Nested config class dependencies from core SDK

## [2.0.0-dev] - 2025-11-20

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