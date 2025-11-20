-- DocVault v2.0 Database Schema
-- PostgreSQL schema for document management system
--
-- Major Changes from v1:
-- - Organizations and Agents use external UUIDs as primary keys (no external_id field)
-- - Removed name, email, agent_type fields (store externally)
-- - Added prefix and path columns to documents for hierarchical organization
-- - Updated indexes to support prefix-based queries

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Organizations Table (v2)
-- Pure reference entity: only stores UUID and metadata
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_organizations_created_at ON organizations (created_at);

-- Agents Table (v2)
-- Pure reference entity: only stores UUID, org membership, and metadata
CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_agents_organization_id ON agents (organization_id);

CREATE INDEX IF NOT EXISTS idx_agents_active ON agents (is_active);

-- Documents Table (v2)
-- Added prefix and path columns for hierarchical organization
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    organization_id UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    name VARCHAR(500) NOT NULL,
    description TEXT,
    filename VARCHAR(500) NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(100),
    storage_path VARCHAR(1000) NOT NULL,
    prefix VARCHAR(500),
    path VARCHAR(1000),
    current_version INTEGER DEFAULT 1,
    status VARCHAR(50) DEFAULT 'active',
    created_by UUID NOT NULL REFERENCES agents (id),
    updated_by UUID REFERENCES agents (id),
    metadata JSONB DEFAULT '{}',
    tags TEXT [],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    search_vector tsvector
);

CREATE INDEX IF NOT EXISTS idx_documents_organization_id ON documents (organization_id);

CREATE INDEX IF NOT EXISTS idx_documents_created_by ON documents (created_by);

CREATE INDEX IF NOT EXISTS idx_documents_status ON documents (status);

CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_documents_name ON documents USING gin (to_tsvector('english', name));

CREATE INDEX IF NOT EXISTS idx_documents_search_vector ON documents USING gin (search_vector);

CREATE INDEX IF NOT EXISTS idx_documents_tags ON documents USING gin (tags);

-- New indexes for hierarchical organization (v2.0)
CREATE INDEX IF NOT EXISTS idx_documents_prefix ON documents (prefix);

CREATE INDEX IF NOT EXISTS idx_documents_path ON documents USING gin (path gin_trgm_ops);

-- Document Versions Table (v2)
-- Uses UUID references for all foreign keys
CREATE TABLE IF NOT EXISTS document_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    document_id UUID NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    filename VARCHAR(500) NOT NULL,
    file_size BIGINT NOT NULL,
    storage_path VARCHAR(1000) NOT NULL,
    mime_type VARCHAR(100),
    change_description TEXT,
    change_type VARCHAR(50),
    created_by UUID NOT NULL REFERENCES agents (id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    UNIQUE (document_id, version_number)
);

CREATE INDEX IF NOT EXISTS idx_document_versions_document_id ON document_versions (document_id);

CREATE INDEX IF NOT EXISTS idx_document_versions_created_at ON document_versions (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_document_versions_version_number ON document_versions (
    document_id,
    version_number DESC
);

-- Document ACL Table (v2)
-- Uses UUID references for all foreign keys
CREATE TABLE IF NOT EXISTS document_acl (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    document_id UUID NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES agents (id) ON DELETE CASCADE,
    permission VARCHAR(50) NOT NULL,
    granted_by UUID NOT NULL REFERENCES agents (id),
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    UNIQUE (
        document_id,
        agent_id,
        permission
    )
);

CREATE INDEX IF NOT EXISTS idx_document_acl_document_id ON document_acl (document_id);

CREATE INDEX IF NOT EXISTS idx_document_acl_agent_id ON document_acl (agent_id);

CREATE INDEX IF NOT EXISTS idx_document_acl_permission ON document_acl (permission);

CREATE INDEX IF NOT EXISTS idx_document_acl_expires_at ON document_acl (expires_at)
WHERE
    expires_at IS NOT NULL;

-- Document Tags Table (v2)
-- Uses UUID references
CREATE TABLE IF NOT EXISTS document_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    document_id UUID NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    tag VARCHAR(100) NOT NULL,
    created_by UUID REFERENCES agents (id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (document_id, tag)
);

CREATE INDEX IF NOT EXISTS idx_document_tags_document_id ON document_tags (document_id);

CREATE INDEX IF NOT EXISTS idx_document_tags_tag ON document_tags (tag);

-- Database Triggers
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

CREATE TRIGGER update_document_acl_updated_at
    BEFORE UPDATE ON document_acl
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE FUNCTION update_document_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', coalesce(NEW.name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(NEW.description, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(array_to_string(NEW.tags, ' '), '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_documents_search_vector
    BEFORE INSERT OR UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_document_search_vector();