-- DocVault v1 to v2 Migration Script
--
-- IMPORTANT: Before running this script:
-- 1. BACKUP YOUR DATABASE: pg_dump doc_vault > doc_vault_v1_backup.sql
-- 2. Test on a copy of your production database first
-- 3. Schedule downtime for your application
--
-- This migration script:
-- - Preserves all data by converting IDs appropriately
-- - Removes external_id fields from organizations and agents
-- - Removes name, email, agent_type from agents
-- - Removes name from organizations
-- - Adds prefix and path columns to documents
-- - Updates indexes for new schema
--
-- Rollback: Use the backup SQL dump: psql doc_vault < doc_vault_v1_backup.sql

-- ============================================================================
-- PHASE 1: CREATE NEW TABLES WITH V2 SCHEMA (Non-destructive)
-- ============================================================================

-- Create temporary backup of v1 data (for validation and debugging)
CREATE TABLE IF NOT EXISTS organizations_v1_backup AS
SELECT *
FROM organizations;

CREATE TABLE IF NOT EXISTS agents_v1_backup AS SELECT * FROM agents;

CREATE TABLE IF NOT EXISTS documents_v1_backup AS
SELECT *
FROM documents;

CREATE TABLE IF NOT EXISTS document_acl_v1_backup AS
SELECT *
FROM document_acl;

CREATE TABLE IF NOT EXISTS document_versions_v1_backup AS
SELECT *
FROM document_versions;

-- ============================================================================
-- PHASE 2: MIGRATION LOGIC
-- ============================================================================

-- Step 1: Drop dependent views (if any exist)
DROP VIEW IF EXISTS document_access CASCADE;

-- Step 2: Drop old indexes that will be removed
DROP INDEX IF EXISTS idx_organizations_external_id;

DROP INDEX IF EXISTS idx_agents_external_id;

-- Step 3: Create new organizations table with v2 schema
CREATE TABLE organizations_v2 (
    id UUID PRIMARY KEY,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Migrate data: Use existing UUID as-is, preserve timestamps and metadata
INSERT INTO
    organizations_v2 (
        id,
        metadata,
        created_at,
        updated_at
    )
SELECT
    id,
    metadata,
    created_at,
    updated_at
FROM organizations;

-- Step 4: Create new agents table with v2 schema
CREATE TABLE agents_v2 (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations_v2 (id) ON DELETE CASCADE,
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Migrate data: Use existing UUID, preserve org relationship and status
INSERT INTO
    agents_v2 (
        id,
        organization_id,
        metadata,
        is_active,
        created_at,
        updated_at
    )
SELECT
    id,
    organization_id,
    metadata,
    is_active,
    created_at,
    updated_at
FROM agents;

-- Add new indexes for v2 agents table
CREATE INDEX idx_agents_organization_id_v2 ON agents_v2 (organization_id);

CREATE INDEX idx_agents_active_v2 ON agents_v2 (is_active);

-- Step 5: Update documents table - add new columns first
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS prefix VARCHAR(500),
ADD COLUMN IF NOT EXISTS path VARCHAR(1000);

-- Generate path column from prefix + name (if prefix exists)
UPDATE documents
SET
    path = CASE
        WHEN prefix IS NOT NULL THEN prefix || name
        ELSE name
    END;

-- Step 6: Create new ACL table with updated constraints
CREATE TABLE document_acl_v2 (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    document_id UUID NOT NULL,
    agent_id UUID NOT NULL,
    permission VARCHAR(50) NOT NULL,
    granted_by UUID NOT NULL,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    UNIQUE (
        document_id,
        agent_id,
        permission
    )
);

-- Migrate ACL data (don't set constraints yet, will do after document migration)
INSERT INTO
    document_acl_v2 (
        id,
        document_id,
        agent_id,
        permission,
        granted_by,
        granted_at,
        updated_at,
        expires_at
    )
SELECT
    id,
    document_id,
    agent_id,
    permission,
    granted_by,
    granted_at,
    updated_at,
    expires_at
FROM document_acl;

-- Step 7: Create new document versions table
CREATE TABLE document_versions_v2 (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    document_id UUID NOT NULL,
    version_number INTEGER NOT NULL,
    filename VARCHAR(500) NOT NULL,
    file_size BIGINT NOT NULL,
    storage_path VARCHAR(1000) NOT NULL,
    mime_type VARCHAR(100),
    change_description TEXT,
    change_type VARCHAR(50),
    created_by UUID NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    UNIQUE (document_id, version_number)
);

-- Migrate document versions
INSERT INTO
    document_versions_v2 (
        id,
        document_id,
        version_number,
        filename,
        file_size,
        storage_path,
        mime_type,
        change_description,
        change_type,
        created_by,
        created_at,
        metadata
    )
SELECT
    id,
    document_id,
    version_number,
    filename,
    file_size,
    storage_path,
    mime_type,
    change_description,
    change_type,
    created_by,
    created_at,
    metadata
FROM document_versions;

-- ============================================================================
-- PHASE 3: DROP OLD TABLES AND RENAME V2 TABLES
-- ============================================================================

-- Drop old foreign key constraints in dependent tables
ALTER TABLE documents
DROP CONSTRAINT IF EXISTS documents_created_by_fkey;

ALTER TABLE documents
DROP CONSTRAINT IF EXISTS documents_updated_by_fkey;

ALTER TABLE documents
DROP CONSTRAINT IF EXISTS documents_organization_id_fkey;

ALTER TABLE document_versions
DROP CONSTRAINT IF EXISTS document_versions_created_by_fkey;

ALTER TABLE document_versions
DROP CONSTRAINT IF EXISTS document_versions_document_id_fkey;

ALTER TABLE document_acl
DROP CONSTRAINT IF EXISTS document_acl_document_id_fkey;

ALTER TABLE document_acl
DROP CONSTRAINT IF EXISTS document_acl_agent_id_fkey;

ALTER TABLE document_acl
DROP CONSTRAINT IF EXISTS document_acl_granted_by_fkey;

ALTER TABLE agents
DROP CONSTRAINT IF EXISTS agents_organization_id_fkey;

ALTER TABLE document_tags
DROP CONSTRAINT IF EXISTS document_tags_document_id_fkey;

ALTER TABLE document_tags
DROP CONSTRAINT IF EXISTS document_tags_created_by_fkey;

-- Drop old tables
DROP TABLE IF EXISTS document_acl CASCADE;

DROP TABLE IF EXISTS document_versions CASCADE;

DROP TABLE IF EXISTS document_tags CASCADE;

DROP TABLE IF EXISTS documents CASCADE;

DROP TABLE IF EXISTS agents CASCADE;

DROP TABLE IF EXISTS organizations CASCADE;

-- Rename v2 tables to standard names
ALTER TABLE organizations_v2 RENAME TO organizations;

ALTER TABLE agents_v2 RENAME TO agents;

ALTER TABLE document_acl_v2 RENAME TO document_acl;

ALTER TABLE document_versions_v2 RENAME TO document_versions;

-- ============================================================================
-- PHASE 4: RESTORE FOREIGN KEYS AND INDEXES
-- ============================================================================

-- Restore document foreign keys
ALTER TABLE documents
ADD CONSTRAINT documents_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
ADD CONSTRAINT documents_created_by_fkey FOREIGN KEY (created_by) REFERENCES agents (id),
ADD CONSTRAINT documents_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES agents (id);

-- Restore document versions foreign keys
ALTER TABLE document_versions
ADD CONSTRAINT document_versions_document_id_fkey FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE,
ADD CONSTRAINT document_versions_created_by_fkey FOREIGN KEY (created_by) REFERENCES agents (id);

-- Restore ACL foreign keys
ALTER TABLE document_acl
ADD CONSTRAINT document_acl_document_id_fkey FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE,
ADD CONSTRAINT document_acl_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES agents (id) ON DELETE CASCADE,
ADD CONSTRAINT document_acl_granted_by_fkey FOREIGN KEY (granted_by) REFERENCES agents (id);

-- Restore document_tags foreign keys
ALTER TABLE document_tags
ADD CONSTRAINT document_tags_document_id_fkey FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE,
ADD CONSTRAINT document_tags_created_by_fkey FOREIGN KEY (created_by) REFERENCES agents (id);

-- Restore agents organization foreign key
ALTER TABLE agents
ADD CONSTRAINT agents_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE CASCADE;

-- Create new v2 indexes
CREATE INDEX idx_documents_prefix ON documents (prefix);

CREATE INDEX idx_documents_path ON documents USING gin (path gin_trgm_ops);

CREATE INDEX idx_organizations_created_at ON organizations (created_at);

CREATE INDEX idx_documents_organization_id ON documents (organization_id);

CREATE INDEX idx_documents_created_by ON documents (created_by);

CREATE INDEX idx_documents_status ON documents (status);

CREATE INDEX idx_documents_created_at ON documents (created_at DESC);

CREATE INDEX idx_documents_name ON documents USING gin (to_tsvector('english', name));

CREATE INDEX idx_documents_search_vector ON documents USING gin (search_vector);

CREATE INDEX idx_documents_tags ON documents USING gin (tags);

CREATE INDEX idx_document_versions_document_id ON document_versions (document_id);

CREATE INDEX idx_document_versions_created_at ON document_versions (created_at DESC);

CREATE INDEX idx_document_versions_version_number ON document_versions (
    document_id,
    version_number DESC
);

CREATE INDEX idx_document_acl_document_id ON document_acl (document_id);

CREATE INDEX idx_document_acl_agent_id ON document_acl (agent_id);

CREATE INDEX idx_document_acl_permission ON document_acl (permission);

CREATE INDEX idx_document_acl_expires_at ON document_acl (expires_at)
WHERE
    expires_at IS NOT NULL;

CREATE INDEX idx_document_tags_document_id ON document_tags (document_id);

CREATE INDEX idx_document_tags_tag ON document_tags (tag);

-- ============================================================================
-- PHASE 5: RECREATE TRIGGERS
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_organizations_updated_at ON organizations;

CREATE TRIGGER update_organizations_updated_at
    BEFORE UPDATE ON organizations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_agents_updated_at ON agents;

CREATE TRIGGER update_agents_updated_at
    BEFORE UPDATE ON agents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_documents_updated_at ON documents;

CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_document_acl_updated_at ON document_acl;

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

DROP TRIGGER IF EXISTS update_documents_search_vector ON documents;

CREATE TRIGGER update_documents_search_vector
    BEFORE INSERT OR UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_document_search_vector();

-- ============================================================================
-- PHASE 6: DATA VALIDATION
-- ============================================================================

-- Verify organization count matches
SELECT 'Organizations migrated: ' || COUNT(*) FROM organizations;

-- Verify agent count matches
SELECT 'Agents migrated: ' || COUNT(*) FROM agents;

-- Verify documents count matches
SELECT 'Documents migrated: ' || COUNT(*) FROM documents;

-- Verify ACL count matches
SELECT 'ACL records migrated: ' || COUNT(*) FROM document_acl;

-- Verify document versions count matches
SELECT 'Document versions migrated: ' || COUNT(*)
FROM document_versions;

-- Check for null organization_id in agents (should be 0)
SELECT 'Agents with null organization_id: ' || COUNT(*)
FROM agents
WHERE
    organization_id IS NULL;

-- Check for orphaned agents (organization doesn't exist)
SELECT 'Orphaned agents: ' || COUNT(*)
FROM agents a
    LEFT JOIN organizations o ON a.organization_id = o.id
WHERE
    o.id IS NULL;

-- Check for null created_by in documents (should be 0)
SELECT 'Documents with null created_by: ' || COUNT(*)
FROM documents
WHERE
    created_by IS NULL;

-- Check for orphaned documents
SELECT 'Orphaned documents: ' || COUNT(*)
FROM documents d
    LEFT JOIN agents a ON d.created_by = a.id
WHERE
    a.id IS NULL;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

-- Backup tables are available for verification:
-- - organizations_v1_backup
-- - agents_v1_backup
-- - documents_v1_backup
-- - document_acl_v1_backup
-- - document_versions_v1_backup
--
-- You can drop these after confirming the migration was successful:
-- DROP TABLE organizations_v1_backup;
-- DROP TABLE agents_v1_backup;
-- DROP TABLE documents_v1_backup;
-- DROP TABLE document_acl_v1_backup;
-- DROP TABLE document_versions_v1_backup;
--
-- Update your application to v2.0.0 and restart services
-- Monitor application logs for any issues
-- After successful operation for 24+ hours, drop backup tables

-- ============================================================================
-- TO ROLLBACK (if needed):
-- ============================================================================
-- psql doc_vault < doc_vault_v1_backup.sql
--
-- Or manually:
-- DROP TABLE IF EXISTS organizations CASCADE;
-- DROP TABLE IF EXISTS agents CASCADE;
-- DROP TABLE IF EXISTS documents CASCADE;
-- DROP TABLE IF EXISTS document_acl CASCADE;
-- DROP TABLE IF EXISTS document_versions CASCADE;
-- DROP TABLE IF EXISTS document_tags CASCADE;
-- ALTER TABLE organizations_v1_backup RENAME TO organizations;
-- ALTER TABLE agents_v1_backup RENAME TO agents;
-- ALTER TABLE documents_v1_backup RENAME TO documents;
-- ALTER TABLE document_acl_v1_backup RENAME TO document_acl;
-- ALTER TABLE document_versions_v1_backup RENAME TO document_versions;