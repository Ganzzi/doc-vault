-- DocVault Database Schema
-- PostgreSQL schema for document management system

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Organizations Table
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    external_id VARCHAR(255) UNIQUE NOT NULL, -- ID from external system
    name VARCHAR(255) NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_organizations_external_id ON organizations (external_id);

CREATE INDEX idx_organizations_created_at ON organizations (created_at);

-- Agents Table
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    external_id VARCHAR(255) UNIQUE NOT NULL, -- ID from external system
    organization_id UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    agent_type VARCHAR(50) NOT NULL DEFAULT 'human', -- 'human', 'ai', 'service'
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_agents_external_id ON agents (external_id);

CREATE INDEX idx_agents_organization_id ON agents (organization_id);

CREATE INDEX idx_agents_type ON agents (agent_type);

CREATE INDEX idx_agents_active ON agents (is_active);

-- Documents Table
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
created_by UUID NOT NULL REFERENCES agents (id),
updated_by UUID REFERENCES agents (id),

-- Metadata
metadata JSONB DEFAULT '{}', tags TEXT [],

-- Timestamps
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

-- Search
search_vector tsvector );

CREATE INDEX idx_documents_organization_id ON documents (organization_id);

CREATE INDEX idx_documents_created_by ON documents (created_by);

CREATE INDEX idx_documents_status ON documents (status);

CREATE INDEX idx_documents_created_at ON documents (created_at DESC);

CREATE INDEX idx_documents_name ON documents USING gin (to_tsvector('english', name));

CREATE INDEX idx_documents_search_vector ON documents USING gin (search_vector);

CREATE INDEX idx_documents_tags ON documents USING gin (tags);

-- Document Versions Table
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
change_type VARCHAR(50), -- 'create', 'update', 'restore'
created_by UUID NOT NULL REFERENCES agents (id),
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

-- Metadata snapshot
metadata JSONB DEFAULT '{}',

    UNIQUE(document_id, version_number)
);

CREATE INDEX idx_document_versions_document_id ON document_versions (document_id);

CREATE INDEX idx_document_versions_created_at ON document_versions (created_at DESC);

CREATE INDEX idx_document_versions_version_number ON document_versions (
    document_id,
    version_number DESC
);

-- Document ACL Table
CREATE TABLE document_acl (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,

-- Permission
permission VARCHAR(50) NOT NULL, -- 'READ', 'WRITE', 'DELETE', 'SHARE', 'ADMIN'

-- Audit
granted_by UUID NOT NULL REFERENCES agents (id),
granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
expires_at TIMESTAMP, -- Optional expiration

-- Prevent duplicate permissions
UNIQUE(document_id, agent_id, permission) );

CREATE INDEX idx_document_acl_document_id ON document_acl (document_id);

CREATE INDEX idx_document_acl_agent_id ON document_acl (agent_id);

CREATE INDEX idx_document_acl_permission ON document_acl (permission);

CREATE INDEX idx_document_acl_expires_at ON document_acl (expires_at)
WHERE
    expires_at IS NOT NULL;

-- Document Tags Table
CREATE TABLE document_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    document_id UUID NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    tag VARCHAR(100) NOT NULL,
    created_by UUID REFERENCES agents (id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (document_id, tag)
);

CREATE INDEX idx_document_tags_document_id ON document_tags (document_id);

CREATE INDEX idx_document_tags_tag ON document_tags (tag);

-- Database Triggers

-- Auto-update updated_at function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers to tables
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

-- Function to update search vector
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

-- Apply search vector trigger
CREATE TRIGGER update_documents_search_vector
    BEFORE INSERT OR UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_document_search_vector();