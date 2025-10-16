# DocVault SDK - Implementation Plan

**Version:** 1.0  
**Date:** October 15, 2025  
**Status:** Design Phase

---

## 📖 Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture Design](#architecture-design)
3. [Database Design](#database-design)
4. [Storage Strategy](#storage-strategy)
5. [API Design](#api-design)
6. [Implementation Phases](#implementation-phases)
7. [File Structure](#file-structure)
8. [Technology Stack](#technology-stack)
9. [Key Design Decisions](#key-design-decisions)
10. [Future Enhancements](#future-enhancements)

---

## 1. Project Overview

### Purpose
DocVault is a scalable Python SDK for document management and collaboration across organizations and AI agents. It provides APIs for drafting, reviewing, editing, and sharing documents — allowing agents to interact with files as humans do in a company-like environment.

### Core Features
- **Document Upload & Management** - Upload, update, delete binary files (PDF, images, exports)
- **Role-Based Access Control** - Bucket per organization, agent-level permissions
- **Version Control** - Maintain document history, restore previous versions
- **Multi-Organization Support** - Isolation between organizations
- **Binary Storage** - MinIO/S3 for raw file storage
- **Metadata Management** - PostgreSQL for documents, roles, permissions

### Future Features (Phase 2)
- PDF manipulation (annotate, merge, split, extract, sign)
- Semantic search and discovery
- Document templates and workflows
- Real-time collaboration
- Audit logs and analytics

---

## 2. Architecture Design

### Three-Layer Architecture

```
┌─────────────────────────────────────────────────────┐
│                   SDK API Layer                     │
│              (core.py - DocVaultSDK)                │
│  High-level methods: upload(), download(), share()  │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│                  Service Layer                      │
│   DocumentService | AccessService | VersionService  │
│         Business logic orchestration                │
└─────────────────────────────────────────────────────┘
                        ↓
┌───────────────────────────┬─────────────────────────┐
│    Repository Layer       │    Storage Layer        │
│  DocumentRepo             │    S3StorageBackend     │
│  OrganizationRepo         │    (MinIO/S3)           │
│  AgentRepo                │                         │
│  VersionRepo              │                         │
│  ACLRepo                  │                         │
└───────────────────────────┴─────────────────────────┘
                        ↓
┌───────────────────────────┬─────────────────────────┐
│      PostgreSQL           │      MinIO/S3           │
│   (Metadata, ACL)         │   (Binary Files)        │
└───────────────────────────┴─────────────────────────┘
```

### Component Responsibilities

#### SDK API Layer (`core.py`)
- **Purpose**: High-level interface for end users
- **Responsibilities**:
  - Initialize and manage service instances
  - Provide clean, intuitive API
  - Handle context manager lifecycle
  - Abstract complexity from users

#### Service Layer (`services/`)
- **Purpose**: Business logic and orchestration
- **Components**:
  - `DocumentService`: Coordinate document operations (upload, download, update)
  - `AccessService`: Manage permissions and access control
  - `VersionService`: Handle versioning logic
- **Responsibilities**:
  - Orchestrate multiple repositories
  - Enforce business rules
  - Handle transactions
  - Bridge storage and database operations

#### Repository Layer (`database/repositories/`)
- **Purpose**: Data access abstraction
- **Pattern**: Repository pattern for each entity
- **Responsibilities**:
  - Execute SQL queries using psqlpy
  - Convert database rows to Pydantic models
  - Handle database-specific errors
  - Provide CRUD operations

#### Storage Layer (`storage/`)
- **Purpose**: Abstract binary file storage
- **Responsibilities**:
  - Upload/download files to S3/MinIO
  - Manage bucket lifecycle
  - Generate presigned URLs
  - Support multiple storage backends

---

## 3. Database Design

### Entity-Relationship Model

```
organizations 1──────* agents
      │                   │
      │                   │
      1                   *
      │                   │
   documents *─────────* document_acl
      │
      │
      1
      │
      *
document_versions
      │
      │
      *
document_tags
```

### Table Schemas

#### 3.1 Organizations Table
```sql
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(255) UNIQUE NOT NULL,  -- ID from external system
    name VARCHAR(255) NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_organizations_external_id ON organizations(external_id);
CREATE INDEX idx_organizations_created_at ON organizations(created_at);
```

**Purpose**: Track organizations (companies, teams, departments)  
**Key Fields**:
- `external_id`: Reference to external system (e.g., your CRM, auth system)
- `metadata`: Flexible JSON for custom fields

#### 3.2 Agents Table
```sql
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(255) UNIQUE NOT NULL,  -- ID from external system
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    agent_type VARCHAR(50) NOT NULL DEFAULT 'human',  -- 'human', 'ai', 'service'
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_agents_external_id ON agents(external_id);
CREATE INDEX idx_agents_organization_id ON agents(organization_id);
CREATE INDEX idx_agents_type ON agents(agent_type);
CREATE INDEX idx_agents_active ON agents(is_active);
```

**Purpose**: Represent users (humans or AI agents) within organizations  
**Key Fields**:
- `agent_type`: Distinguish between human users, AI agents, and service accounts
- `external_id`: Reference to your user management system

#### 3.3 Documents Table
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(500) NOT NULL,
    description TEXT,
    filename VARCHAR(500) NOT NULL,
    file_size BIGINT NOT NULL,  -- bytes
    mime_type VARCHAR(100),
    storage_path VARCHAR(1000) NOT NULL,  -- S3 path
    current_version INTEGER DEFAULT 1,
    status VARCHAR(50) DEFAULT 'active',  -- 'draft', 'active', 'archived', 'deleted'
    
    -- Ownership
    created_by UUID NOT NULL REFERENCES agents(id),
    updated_by UUID REFERENCES agents(id),
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    tags TEXT[],
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Search
    search_vector tsvector
);

CREATE INDEX idx_documents_organization_id ON documents(organization_id);
CREATE INDEX idx_documents_created_by ON documents(created_by);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_created_at ON documents(created_at DESC);
CREATE INDEX idx_documents_name ON documents USING gin(to_tsvector('english', name));
CREATE INDEX idx_documents_search_vector ON documents USING gin(search_vector);
CREATE INDEX idx_documents_tags ON documents USING gin(tags);
```

**Purpose**: Core document metadata  
**Key Fields**:
- `storage_path`: Location in S3/MinIO
- `current_version`: Active version number
- `status`: Lifecycle state
- `search_vector`: Full-text search support

#### 3.4 Document Versions Table
```sql
CREATE TABLE document_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    
    -- File info
    filename VARCHAR(500) NOT NULL,
    file_size BIGINT NOT NULL,
    storage_path VARCHAR(1000) NOT NULL,
    mime_type VARCHAR(100),
    
    -- Change tracking
    change_description TEXT,
    change_type VARCHAR(50),  -- 'create', 'update', 'restore'
    created_by UUID NOT NULL REFERENCES agents(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Metadata snapshot
    metadata JSONB DEFAULT '{}',
    
    UNIQUE(document_id, version_number)
);

CREATE INDEX idx_document_versions_document_id ON document_versions(document_id);
CREATE INDEX idx_document_versions_created_at ON document_versions(created_at DESC);
CREATE INDEX idx_document_versions_version_number ON document_versions(document_id, version_number DESC);
```

**Purpose**: Version history for documents  
**Key Fields**:
- `version_number`: Incremental version (1, 2, 3...)
- `change_type`: Track how version was created
- `metadata`: Snapshot of document metadata at version time

#### 3.5 Document ACL Table
```sql
CREATE TABLE document_acl (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    
    -- Permission
    permission VARCHAR(50) NOT NULL,  -- 'READ', 'WRITE', 'DELETE', 'SHARE', 'ADMIN'
    
    -- Audit
    granted_by UUID NOT NULL REFERENCES agents(id),
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,  -- Optional expiration
    
    -- Prevent duplicate permissions
    UNIQUE(document_id, agent_id, permission)
);

CREATE INDEX idx_document_acl_document_id ON document_acl(document_id);
CREATE INDEX idx_document_acl_agent_id ON document_acl(agent_id);
CREATE INDEX idx_document_acl_permission ON document_acl(permission);
CREATE INDEX idx_document_acl_expires_at ON document_acl(expires_at) WHERE expires_at IS NOT NULL;
```

**Purpose**: Fine-grained access control  
**Permissions**:
- `READ`: View document and download
- `WRITE`: Edit document metadata and replace content
- `DELETE`: Delete document
- `SHARE`: Grant access to other agents
- `ADMIN`: Full control (all permissions)

**Access Rules**:
1. Document creator automatically gets `ADMIN` permission
2. Agents can only see documents in their organization (org-level isolation)
3. Within organization, ACL determines what each agent can access
4. Permissions can expire (time-based access)

#### 3.6 Document Tags Table (Optional)
```sql
CREATE TABLE document_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    tag VARCHAR(100) NOT NULL,
    created_by UUID REFERENCES agents(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(document_id, tag)
);

CREATE INDEX idx_document_tags_document_id ON document_tags(document_id);
CREATE INDEX idx_document_tags_tag ON document_tags(tag);
```

**Purpose**: Tag-based organization and search

### Database Triggers

#### Auto-update `updated_at`
```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_organizations_updated_at
    BEFORE UPDATE ON organizations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agents_updated_at
    BEFORE UPDATE ON agents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

#### Auto-update Search Vector
```sql
CREATE OR REPLACE FUNCTION update_document_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := 
        setweight(to_tsvector('english', COALESCE(NEW.name, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'B');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_documents_search_vector
    BEFORE INSERT OR UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_document_search_vector();
```

---

## 4. Storage Strategy

### MinIO/S3 Bucket Architecture

#### Bucket Naming Convention
```
doc-vault-org-{organization_id}
```

Example:
- Organization `org-123` → Bucket: `doc-vault-org-123`
- Organization `org-456` → Bucket: `doc-vault-org-456`

**Benefits**:
- Strong isolation between organizations
- Easy to apply bucket-level policies
- Simplifies billing and quotas
- Can use different regions per org

#### Object Path Structure
```
{document_id}/v{version_number}/{filename}
```

Examples:
- Current version: `abc-123/v3/report.pdf`
- Old version: `abc-123/v1/report.pdf`
- Old version: `abc-123/v2/report.pdf`

**Benefits**:
- All versions grouped by document
- Easy to list all versions
- Simple to restore (copy old version to new)

#### Storage Operations

**Upload Document (New)**:
1. Generate document UUID
2. Upload to: `{bucket}/{doc_id}/v1/{filename}`
3. Store metadata in PostgreSQL with `storage_path`

**Replace Document (Update)**:
1. Increment version number (v2, v3, etc.)
2. Upload to: `{bucket}/{doc_id}/v{new_version}/{filename}`
3. Create entry in `document_versions` table
4. Update `documents.current_version`

**Restore Version**:
1. Copy old version object: `v2` → `v4` (new version)
2. Create version record with `change_type='restore'`
3. Update `documents.current_version = 4`

**Delete Document**:
- **Soft delete**: Set `status='deleted'` in database
- **Hard delete**: Delete all version objects from S3, delete database records

### Storage Backend Interface

```python
# storage/base.py
class StorageBackend(ABC):
    @abstractmethod
    async def upload(self, bucket: str, path: str, data: bytes, 
                     content_type: str) -> str:
        """Upload file and return storage URL"""
        
    @abstractmethod
    async def download(self, bucket: str, path: str) -> bytes:
        """Download file as bytes"""
        
    @abstractmethod
    async def delete(self, bucket: str, path: str) -> None:
        """Delete file"""
        
    @abstractmethod
    async def exists(self, bucket: str, path: str) -> bool:
        """Check if file exists"""
        
    @abstractmethod
    async def create_bucket(self, bucket: str) -> None:
        """Create bucket if not exists"""
        
    @abstractmethod
    async def generate_presigned_url(self, bucket: str, path: str, 
                                      expiry: int = 3600) -> str:
        """Generate temporary download URL"""
```

---

## 5. API Design

### SDK Initialization

```python
from doc_vault import DocVaultSDK
from doc_vault.config import Config

# Option 1: From environment variables (.env file)
async with DocVaultSDK() as vault:
    # Use vault
    pass

# Option 2: Explicit configuration
config = Config(
    postgres_host="localhost",
    postgres_port=5432,
    postgres_user="postgres",
    postgres_password="password",
    postgres_db="doc_vault",
    minio_endpoint="localhost:9000",
    minio_access_key="minioadmin",
    minio_secret_key="minioadmin",
    bucket_prefix="doc-vault"
)

async with DocVaultSDK(config=config) as vault:
    # Use vault
    pass
```

### Core API Methods

#### Document Operations

```python
# Upload document
document = await vault.upload(
    file_path="./report.pdf",           # Local file path
    name="Q4 Financial Report",         # Display name
    description="2024 Q4 results",      # Optional description
    organization_id="org-123",          # Organization
    agent_id="agent-456",               # Uploader (creator)
    tags=["finance", "2024"],           # Optional tags
    metadata={"department": "finance"}  # Custom metadata
)

# Download document
file_bytes = await vault.download(
    document_id=document.id,
    agent_id="agent-456",               # Requester (for permission check)
    version=None                        # None = current, or specify version number
)

# Update document metadata
updated_doc = await vault.update_metadata(
    document_id=document.id,
    agent_id="agent-456",
    name="Q4 Financial Report - Final",
    description="Updated description",
    tags=["finance", "2024", "final"],
    metadata={"status": "approved"}
)

# Replace document content (creates new version)
new_version = await vault.replace(
    document_id=document.id,
    file_path="./report_v2.pdf",
    agent_id="agent-456",
    change_description="Fixed typos on page 3"
)

# Delete document
await vault.delete(
    document_id=document.id,
    agent_id="agent-456",
    hard_delete=False  # Soft delete by default
)

# List documents
documents = await vault.list_documents(
    organization_id="org-123",
    agent_id="agent-456",                # Only shows accessible docs
    status="active",                     # Filter by status
    tags=["finance"],                    # Filter by tags
    limit=50,
    offset=0
)

# Search documents
results = await vault.search(
    query="financial report",
    organization_id="org-123",
    agent_id="agent-456",
    limit=20
)
```

#### Access Control

```python
# Share document with another agent
await vault.share(
    document_id=document.id,
    agent_id="agent-789",               # Agent to grant access to
    permission="READ",                   # READ, WRITE, DELETE, SHARE, ADMIN
    granted_by="agent-456",             # Who is granting access
    expires_at=None                     # Optional expiration datetime
)

# Revoke access
await vault.revoke(
    document_id=document.id,
    agent_id="agent-789",
    permission="READ",
    revoked_by="agent-456"
)

# Check if agent has permission
has_access = await vault.check_permission(
    document_id=document.id,
    agent_id="agent-789",
    permission="READ"
)

# List accessible documents for agent
accessible_docs = await vault.list_accessible_documents(
    agent_id="agent-789",
    organization_id="org-123",
    permission="READ"  # Optional: filter by permission level
)

# Get document permissions
permissions = await vault.get_document_permissions(
    document_id=document.id,
    agent_id="agent-456"  # Must have ADMIN permission
)
```

#### Version Management

```python
# List document versions
versions = await vault.get_versions(
    document_id=document.id,
    agent_id="agent-456"
)

# Download specific version
old_content = await vault.download(
    document_id=document.id,
    agent_id="agent-456",
    version=2  # Specific version number
)

# Restore previous version (creates new version)
restored = await vault.restore_version(
    document_id=document.id,
    version_number=2,
    agent_id="agent-456",
    change_description="Restored version 2"
)

# Get version details
version_info = await vault.get_version_info(
    document_id=document.id,
    version_number=2,
    agent_id="agent-456"
)
```

#### Organization & Agent Management

```python
# Register organization (idempotent)
org = await vault.register_organization(
    external_id="org-123",
    name="Acme Corporation",
    metadata={"industry": "technology"}
)

# Register agent
agent = await vault.register_agent(
    external_id="agent-456",
    organization_id="org-123",
    name="John Doe",
    email="john@acme.com",
    agent_type="human",
    metadata={"role": "engineer"}
)

# Get organization info
org_info = await vault.get_organization(external_id="org-123")

# Get agent info
agent_info = await vault.get_agent(external_id="agent-456")
```

---

## 6. Implementation Phases

### Phase 1: Foundation (Days 1-2)
**Goal**: Set up project structure and core infrastructure

**Tasks**:
1. Create project structure and directories
2. Configure `pyproject.toml` with dependencies
3. Create `.env.example` and `.gitignore`
4. Build exception hierarchy (`exceptions.py`)
5. Implement configuration layer (`config.py`)
6. Create all `__init__.py` files

**Dependencies**: psqlpy, pydantic, pydantic-settings, minio, python-dotenv

**Deliverable**: Project can be installed, configured, and imported

---

### Phase 2: Database Layer (Days 3-5)
**Goal**: Set up PostgreSQL integration with psqlpy

**Tasks**:
1. Create `database/postgres_manager.py` (connection pool)
2. Write `sql/schema.sql` (all tables, indexes, triggers)
3. Create Pydantic models in `database/schemas/`:
   - `organization.py`
   - `agent.py`
   - `document.py`
   - `version.py`
   - `acl.py`
4. Create `database/init_db.py` (database initialization script)

**Deliverable**: Can initialize database and connect with psqlpy

---

### Phase 3: Repository Layer (Days 6-8)
**Goal**: Build data access layer

**Tasks**:
1. Create `database/repositories/base.py` (base repository pattern)
2. Implement repositories:
   - `organization.py` (OrganizationRepository)
   - `agent.py` (AgentRepository)
   - `document.py` (DocumentRepository)
   - `version.py` (VersionRepository)
   - `acl.py` (ACLRepository)
3. Add comprehensive error handling
4. Write repository unit tests

**Deliverable**: All database entities have CRUD operations

---

### Phase 4: Storage Layer (Days 9-10)
**Goal**: Implement S3/MinIO integration

**Tasks**:
1. Create `storage/base.py` (abstract storage interface)
2. Implement `storage/s3_client.py` (MinIO/S3 backend)
3. Add bucket lifecycle management
4. Implement presigned URL generation
5. Write storage unit tests

**Deliverable**: Can upload, download, delete files from MinIO/S3

---

### Phase 5: Service Layer (Days 11-14)
**Goal**: Implement business logic

**Tasks**:
1. Create `services/document_service.py`:
   - upload_document()
   - download_document()
   - update_metadata()
   - delete_document()
   - replace_document()
   - list_documents()
   - search_documents()
2. Create `services/access_service.py`:
   - grant_access()
   - revoke_access()
   - check_permission()
   - list_accessible_documents()
3. Create `services/version_service.py`:
   - create_version()
   - list_versions()
   - restore_version()
   - get_version_content()
4. Write service integration tests

**Deliverable**: Core business logic implemented and tested

---

### Phase 6: SDK API Layer (Days 15-16)
**Goal**: Create high-level SDK interface

**Tasks**:
1. Implement `core.py` (DocVaultSDK class)
2. Add context manager support
3. Implement all public API methods
4. Configure `__init__.py` exports
5. Write end-to-end tests

**Deliverable**: Complete SDK ready for use

---

### Phase 7: Documentation & Examples (Days 17-18)
**Goal**: Make SDK usable by developers

**Tasks**:
1. Write comprehensive `README.md`
2. Create example scripts:
   - `examples/basic_usage.py`
   - `examples/access_control.py`
   - `examples/versioning.py`
   - `examples/multi_org.py`
3. Write `DEVELOPMENT.md` (local setup guide)
4. Create API reference documentation
5. Write deployment guide

**Deliverable**: Complete documentation for users and contributors

---

### Phase 8: Testing & Polish (Days 19-20)
**Goal**: Ensure quality and reliability

**Tasks**:
1. Write comprehensive test suite
2. Set up CI/CD pipeline
3. Performance testing and optimization
4. Security audit
5. Docker Compose for local development
6. Version 1.0 release

**Deliverable**: Production-ready SDK v1.0

---

## 7. File Structure

```
doc_vault/
├── doc_vault/                      # Main package
│   ├── __init__.py                # Package exports
│   ├── config.py                  # Configuration management
│   ├── core.py                    # Main SDK API
│   ├── exceptions.py              # Custom exceptions
│   │
│   ├── database/                  # Database layer
│   │   ├── __init__.py
│   │   ├── postgres_manager.py   # PSQLPy connection pool
│   │   ├── init_db.py            # Database initialization
│   │   │
│   │   ├── schemas/               # Pydantic models
│   │   │   ├── __init__.py
│   │   │   ├── organization.py
│   │   │   ├── agent.py
│   │   │   ├── document.py
│   │   │   ├── version.py
│   │   │   └── acl.py
│   │   │
│   │   └── repositories/          # Data access layer
│   │       ├── __init__.py
│   │       ├── base.py           # Base repository
│   │       ├── organization.py
│   │       ├── agent.py
│   │       ├── document.py
│   │       ├── version.py
│   │       └── acl.py
│   │
│   ├── storage/                   # Storage layer
│   │   ├── __init__.py
│   │   ├── base.py               # Storage interface (ABC)
│   │   ├── s3_client.py          # S3/MinIO implementation
│   │   └── local.py              # Local storage (dev/testing)
│   │
│   ├── services/                  # Business logic layer
│   │   ├── __init__.py
│   │   ├── document_service.py   # Document operations
│   │   ├── access_service.py     # Access control
│   │   └── version_service.py    # Version management
│   │
│   └── sql/                       # SQL scripts
│       └── schema.sql            # Database schema
│
├── tests/                         # Test suite
│   ├── __init__.py
│   ├── conftest.py               # Pytest configuration
│   ├── test_config.py
│   ├── test_postgres_manager.py
│   ├── test_repositories/
│   │   ├── test_document_repo.py
│   │   ├── test_agent_repo.py
│   │   └── ...
│   ├── test_storage/
│   │   └── test_s3_client.py
│   ├── test_services/
│   │   ├── test_document_service.py
│   │   ├── test_access_service.py
│   │   └── test_version_service.py
│   └── test_core.py              # End-to-end tests
│
├── examples/                      # Usage examples
│   ├── basic_usage.py
│   ├── access_control.py
│   ├── versioning.py
│   └── multi_org.py
│
├── docs/                          # Documentation
│   ├── PLAN.md                   # This file
│   ├── psqlpy-complete-guide.md  # PSQLPy reference
│   └── API.md                    # API reference (future)
│
├── pyproject.toml                 # Poetry configuration
├── setup.py                       # Setup script
├── README.md                      # Main documentation
├── DEVELOPMENT.md                 # Development guide
├── .env.example                   # Example environment variables
├── .gitignore                     # Git ignore rules
└── docker-compose.yml             # Local development stack (future)
```

---

## 8. Technology Stack

### Core Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `psqlpy` | Latest | PostgreSQL async driver (high-performance) |
| `pydantic` | ^2.0 | Data validation and settings |
| `pydantic-settings` | ^2.0 | Environment-based configuration |
| `minio` | Latest | MinIO/S3 client |
| `python-dotenv` | Latest | Environment variable loading |

### Development Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `pytest` | ^7.0 | Testing framework |
| `pytest-asyncio` | ^0.21 | Async test support |
| `pytest-cov` | ^4.0 | Coverage reporting |
| `black` | ^23.0 | Code formatting |
| `ruff` | ^0.1 | Fast Python linter |
| `mypy` | ^1.0 | Static type checking |

### Infrastructure

| Component | Purpose |
|-----------|---------|
| PostgreSQL 14+ | Metadata, ACL, search |
| MinIO or AWS S3 | Binary file storage |
| Docker Compose | Local development |

---

## 9. Key Design Decisions

### 9.1 Why PSQLPy?
- **Performance**: Rust-based driver, faster than psycopg2/asyncpg
- **Async-first**: Native async/await support
- **Type-safe**: Uses PostgreSQL's `$1, $2` placeholders
- **Modern**: Active development and maintained

### 9.2 Repository Pattern
- **Separation of Concerns**: Business logic separate from data access
- **Testability**: Easy to mock repositories in tests
- **Maintainability**: Changes to database don't affect services
- **Reusability**: Common patterns in base repository

### 9.3 Service Layer
- **Orchestration**: Coordinates multiple repositories and storage
- **Business Rules**: Enforce permissions, validation, workflows
- **Transactions**: Handle multi-step operations atomically
- **Abstraction**: Hide complexity from SDK users

### 9.4 Bucket-per-Organization
- **Isolation**: Strong separation between organizations
- **Security**: Easier to apply bucket policies
- **Scalability**: Can distribute across regions
- **Billing**: Per-organization cost tracking

**Alternative Considered**: Single bucket with prefixes
- Rejected: Harder to enforce isolation, mixing data

### 9.5 Version Storage Strategy
- **Approach**: Store all versions as separate S3 objects
- **Trade-off**: More storage used, but simpler and faster
- **Benefit**: No need to reconstruct versions from deltas
- **Cost**: Acceptable for document management use case

**Alternative Considered**: Delta-based versioning
- Rejected: Complex, slow to reconstruct, error-prone

### 9.6 Soft Delete by Default
- **Approach**: Mark documents as `status='deleted'` instead of removing
- **Benefit**: Can recover accidentally deleted documents
- **Trade-off**: Need periodic cleanup job
- **Hard Delete**: Available as explicit option

### 9.7 External ID References
- **Approach**: Organizations and agents use `external_id` field
- **Benefit**: SDK doesn't manage user/org lifecycle
- **Use Case**: Integrate with existing auth systems
- **Pattern**: Call `register_organization()` / `register_agent()` at runtime

### 9.8 Permission Model
- **Granular**: Multiple permission types (READ, WRITE, DELETE, SHARE, ADMIN)
- **Flexible**: Can grant individual permissions
- **Expirable**: Optional time-based access
- **Auditable**: Track who granted access and when

### 9.9 Async-Only API
- **Decision**: All SDK methods are async
- **Benefit**: Better performance, non-blocking I/O
- **Trade-off**: Users must use `async with` and `await`
- **Justification**: Document operations often slow (S3, DB), async is natural fit

---

## 10. Future Enhancements

### Phase 2 Features (After v1.0)

#### 10.1 PDF Processing
```python
from doc_vault import DocVaultSDK

async with DocVaultSDK() as vault:
    # Annotate PDF
    await vault.pdf.annotate(
        document_id=doc_id,
        agent_id=agent_id,
        annotations=[
            {"page": 1, "type": "highlight", "text": "Important"},
            {"page": 2, "type": "comment", "text": "Needs review"}
        ]
    )
    
    # Merge PDFs
    merged = await vault.pdf.merge(
        document_ids=[doc1_id, doc2_id, doc3_id],
        output_name="Combined Report",
        agent_id=agent_id
    )
    
    # Extract pages
    extracted = await vault.pdf.extract_pages(
        document_id=doc_id,
        pages=[1, 2, 5],
        output_name="Summary Pages",
        agent_id=agent_id
    )
    
    # Sign PDF
    await vault.pdf.sign(
        document_id=doc_id,
        agent_id=agent_id,
        certificate=cert_data,
        signature_field="signature1"
    )
```

**Dependencies**: PyMuPDF (fitz), python-docx

#### 10.2 Semantic Search
```python
# Index documents
await vault.index_document(
    document_id=doc_id,
    extract_text=True  # Extract text from PDF/DOCX
)

# Semantic search
results = await vault.search_semantic(
    query="quarterly financial performance",
    organization_id="org-123",
    agent_id="agent-456",
    limit=10
)
```

**Dependencies**: pgvector extension, sentence-transformers

#### 10.3 Document Templates
```python
# Create template
template = await vault.create_template(
    name="Sales Proposal Template",
    file_path="./template.pdf",
    variables=["client_name", "amount", "date"],
    organization_id="org-123"
)

# Generate from template
document = await vault.generate_from_template(
    template_id=template.id,
    variables={
        "client_name": "Acme Corp",
        "amount": "$50,000",
        "date": "2025-10-15"
    },
    agent_id="agent-456"
)
```

#### 10.4 Real-time Collaboration
```python
# Start editing session
session = await vault.start_session(
    document_id=doc_id,
    agent_id="agent-456"
)

# Lock document
await vault.lock(document_id=doc_id, agent_id="agent-456")

# Release lock
await vault.unlock(document_id=doc_id, agent_id="agent-456")

# Get active editors
editors = await vault.get_active_editors(document_id=doc_id)
```

**Dependencies**: WebSocket support, Redis for session management

#### 10.5 Audit Logs
```python
# Query audit trail
logs = await vault.get_audit_logs(
    document_id=doc_id,
    start_date="2025-01-01",
    end_date="2025-12-31",
    action_types=["upload", "download", "share"]
)

# Example log entry:
# {
#   "timestamp": "2025-10-15T10:30:00Z",
#   "agent_id": "agent-456",
#   "action": "download",
#   "document_id": "doc-123",
#   "ip_address": "192.168.1.1",
#   "metadata": {"version": 3}
# }
```

**New Table**: `audit_logs`

#### 10.6 Document Workflows
```python
# Create approval workflow
workflow = await vault.create_workflow(
    name="Document Approval",
    steps=[
        {"type": "review", "approvers": ["agent-789"]},
        {"type": "approve", "approvers": ["agent-999"]},
        {"type": "publish"}
    ]
)

# Submit document to workflow
await vault.submit_to_workflow(
    document_id=doc_id,
    workflow_id=workflow.id,
    agent_id="agent-456"
)

# Approve step
await vault.approve_workflow_step(
    document_id=doc_id,
    step_number=1,
    agent_id="agent-789",
    approved=True,
    comments="Looks good"
)
```

#### 10.7 Document Analytics
```python
# Get document statistics
stats = await vault.get_document_stats(document_id=doc_id)
# Returns: views, downloads, shares, last_accessed, etc.

# Organization analytics
org_stats = await vault.get_organization_stats(
    organization_id="org-123"
)
# Returns: total_documents, storage_used, active_agents, etc.
```

#### 10.8 Bulk Operations
```python
# Bulk upload
documents = await vault.bulk_upload(
    files=[
        {"path": "./file1.pdf", "name": "Doc 1"},
        {"path": "./file2.pdf", "name": "Doc 2"},
        # ... up to 100 files
    ],
    organization_id="org-123",
    agent_id="agent-456"
)

# Bulk share
await vault.bulk_share(
    document_ids=[doc1_id, doc2_id, doc3_id],
    agent_ids=["agent-789", "agent-999"],
    permission="READ",
    granted_by="agent-456"
)

# Bulk delete
await vault.bulk_delete(
    document_ids=[doc1_id, doc2_id],
    agent_id="agent-456"
)
```

#### 10.9 Document Comparison
```python
# Compare two versions
diff = await vault.compare_versions(
    document_id=doc_id,
    version_a=2,
    version_b=3,
    agent_id="agent-456"
)

# Returns:
# {
#   "changes": {
#     "metadata": {"name": {"old": "Report", "new": "Final Report"}},
#     "content_diff": "..." # Text diff for supported formats
#   }
# }
```

#### 10.10 Export/Import
```python
# Export organization data
export_path = await vault.export_organization(
    organization_id="org-123",
    include_files=True,  # Include binary files or just metadata
    agent_id="agent-456"
)

# Import organization data
await vault.import_organization(
    import_path="./export.zip",
    organization_id="org-456",
    agent_id="agent-789"
)
```

---

## Implementation Checklist

### Phase 1: Foundation ✓
- [x] Create directory structure
- [x] Configure pyproject.toml
- [x] Create .env.example
- [x] Create .gitignore
- [x] Build exceptions.py
- [x] Build config.py
- [x] Create all __init__.py files

### Phase 2: Database Layer ✓
- [x] Create postgres_manager.py
- [x] Write schema.sql
- [x] Create organization.py schema
- [x] Create agent.py schema
- [x] Create document.py schema
- [x] Create version.py schema
- [x] Create acl.py schema
- [x] Create init_db.py script

### Phase 3: Repository Layer ✓
- [ ] Create base.py repository
- [ ] Create organization.py repository
- [ ] Create agent.py repository
- [ ] Create document.py repository
- [ ] Create version.py repository
- [ ] Create acl.py repository

### Phase 4: Storage Layer ✓
- [ ] Create base.py storage interface
- [ ] Create s3_client.py implementation
- [ ] Test bucket operations
- [ ] Test file upload/download

### Phase 5: Service Layer ✓
- [ ] Create document_service.py
- [ ] Create access_service.py
- [ ] Create version_service.py
- [ ] Write service integration tests

### Phase 6: SDK API ✓
- [ ] Create core.py (DocVaultSDK)
- [ ] Add context manager support
- [ ] Implement all public methods
- [ ] Configure package exports
- [ ] Write end-to-end tests

### Phase 7: Documentation ✓
- [ ] Write README.md
- [ ] Create basic_usage.py example
- [ ] Create access_control.py example
- [ ] Create versioning.py example
- [ ] Create multi_org.py example
- [ ] Write DEVELOPMENT.md

### Phase 8: Polish ✓
- [ ] Complete test suite
- [ ] Set up CI/CD
- [ ] Performance testing
- [ ] Security audit
- [ ] Create docker-compose.yml
- [ ] Release v1.0

---

## Conclusion

This plan provides a comprehensive roadmap for building DocVault SDK from foundation to production. The architecture is designed for scalability, maintainability, and extensibility.

**Key Success Factors**:
1. Follow psqlpy patterns exactly (see docs/psqlpy-complete-guide.md)
2. Use repository pattern consistently
3. Keep services focused and testable
4. Maintain strong isolation between organizations
5. Write comprehensive tests
6. Document as you build

**Timeline**: 20 days for v1.0 (essential features), then iterate with Phase 2 features.

**Next Step**: Begin Phase 1 implementation - project setup and configuration.
