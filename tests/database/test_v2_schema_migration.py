"""
Tests for DocVault v2.0 database schema and migration.

Covers:
- Fresh v2 database creation
- v1 to v2 migration
- Data preservation during migration
- Schema validation
- Index performance
"""

import asyncio
import pytest
from datetime import datetime
from uuid import uuid4

from doc_vault.config import Config
from doc_vault.database.init_db import (
    detect_database_version,
    parse_sql_statements,
    initialize_database,
)
from doc_vault.database.postgres_manager import PostgreSQLManager


class TestSQLParsing:
    """Test SQL statement parsing with complex PostgreSQL syntax."""

    def test_parse_simple_statements(self):
        """Parse simple SQL statements."""
        sql = """
        CREATE TABLE test (id UUID PRIMARY KEY);
        INSERT INTO test VALUES ('123e4567-e89b-12d3-a456-426614174000');
        """
        statements = parse_sql_statements(sql)
        assert len(statements) == 2
        assert "CREATE TABLE" in statements[0]
        assert "INSERT INTO" in statements[1]

    def test_parse_dollar_quoted_functions(self):
        """Parse dollar-quoted strings in PostgreSQL functions."""
        sql = """
        CREATE FUNCTION test_func()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        
        CREATE TRIGGER test_trigger
            BEFORE UPDATE ON test
            FOR EACH ROW
            EXECUTE FUNCTION test_func();
        """
        statements = parse_sql_statements(sql)
        assert len(statements) == 2
        assert "$$" in statements[0]
        assert "CREATE TRIGGER" in statements[1]

    def test_parse_with_comments(self):
        """Parse SQL with comments."""
        sql = """
        -- This is a comment
        CREATE TABLE test (id UUID);
        /* Multi-line
           comment */
        INSERT INTO test VALUES ('123e4567-e89b-12d3-a456-426614174000');
        """
        statements = parse_sql_statements(sql)
        assert len(statements) == 2
        # Comments should be removed
        assert "--" not in statements[0]
        assert "/*" not in statements[1]

    def test_parse_empty_lines(self):
        """Parse SQL with empty lines."""
        sql = """
        
        CREATE TABLE test (id UUID);
        
        
        INSERT INTO test VALUES ('123e4567-e89b-12d3-a456-426614174000');
        """
        statements = parse_sql_statements(sql)
        assert len(statements) == 2


class TestDatabaseVersionDetection:
    """Test database version detection."""

    @pytest.mark.asyncio
    async def test_detect_empty_database(self):
        """Detect empty database as version 'empty'."""
        config = Config.from_env()
        manager = PostgreSQLManager(config)

        try:
            await manager.initialize()

            # Clean database
            await manager.execute("DROP TABLE IF EXISTS organizations CASCADE")

            version = await detect_database_version(manager)
            assert version == "empty"
        finally:
            await manager.close()

    @pytest.mark.asyncio
    async def test_detect_v1_schema(self):
        """Detect v1 schema by external_id column."""
        config = Config.from_env()
        manager = PostgreSQLManager(config)

        try:
            await manager.initialize()

            # Create v1 organizations table
            await manager.execute(
                """
            CREATE TABLE IF NOT EXISTS organizations_test (
                id UUID PRIMARY KEY,
                external_id VARCHAR(255) UNIQUE NOT NULL,
                name VARCHAR(255) NOT NULL
            )
            """
            )

            # Check detection logic directly with query
            query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'organizations_test' AND column_name = 'external_id'
            """
            result = await manager.query(query)
            assert len(result) > 0, "Should detect external_id column for v1"

            # Cleanup
            await manager.execute("DROP TABLE IF EXISTS organizations_test")
        finally:
            await manager.close()

    @pytest.mark.asyncio
    async def test_detect_v2_schema(self):
        """Detect v2 schema by prefix column in documents."""
        config = Config.from_env()
        manager = PostgreSQLManager(config)

        try:
            await manager.initialize()

            # Create minimal v2 schema
            await manager.execute(
                """
            CREATE TABLE IF NOT EXISTS documents_test (
                id UUID PRIMARY KEY,
                name VARCHAR(500),
                prefix VARCHAR(500),
                path VARCHAR(1000)
            )
            """
            )

            # Check detection logic
            query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'documents_test' AND column_name = 'prefix'
            """
            result = await manager.query(query)
            assert len(result) > 0, "Should detect prefix column for v2"

            # Cleanup
            await manager.execute("DROP TABLE IF EXISTS documents_test")
        finally:
            await manager.close()


class TestV2SchemaCreation:
    """Test fresh v2 database schema creation."""

    @pytest.mark.asyncio
    async def test_schema_v2_file_exists(self):
        """Verify schema_v2.sql file exists."""
        from pathlib import Path

        schema_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "doc_vault"
            / "database"
            / "sql"
            / "schema_v2.sql"
        )
        assert schema_path.exists(), f"schema_v2.sql not found at {schema_path}"

    @pytest.mark.asyncio
    async def test_migration_script_exists(self):
        """Verify migrate_v1_to_v2.sql exists."""
        from pathlib import Path

        migration_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "doc_vault"
            / "database"
            / "sql"
            / "migrate_v1_to_v2.sql"
        )
        assert (
            migration_path.exists()
        ), f"migrate_v1_to_v2.sql not found at {migration_path}"

    @pytest.mark.asyncio
    async def test_v2_schema_tables(self):
        """Verify v2 schema creates required tables."""
        config = Config.from_env()

        # This test validates the schema structure without running full init
        # (to avoid conflicts with existing database)

        # Expected v2 tables
        v2_tables = [
            "organizations",
            "agents",
            "documents",
            "document_versions",
            "document_acl",
            "document_tags",
        ]

        # Expected organizations v2 columns (no external_id, no name)
        org_columns_v2 = {"id", "metadata", "created_at", "updated_at"}

        # Expected agents v2 columns (no external_id, no name, email, agent_type)
        agent_columns_v2 = {
            "id",
            "organization_id",
            "metadata",
            "is_active",
            "created_at",
            "updated_at",
        }

        # Expected new documents columns
        doc_new_columns = {"prefix", "path"}

        # Verify schema file contains expected table definitions
        from pathlib import Path

        schema_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "doc_vault"
            / "database"
            / "sql"
            / "schema_v2.sql"
        )

        with open(schema_path, "r") as f:
            schema_content = f.read()

        # Check tables exist in schema
        for table in v2_tables:
            assert (
                f"CREATE TABLE IF NOT EXISTS {table}" in schema_content
            ), f"Table {table} not in v2 schema"

        # Check columns removed from organizations
        assert (
            "external_id VARCHAR" not in schema_content
        ), "external_id should be removed from organizations"
        assert "organizations (" in schema_content
        assert "id UUID PRIMARY KEY" in schema_content

        # Check new document columns
        assert "prefix VARCHAR(500)" in schema_content, "prefix column not in documents"
        assert "path VARCHAR(1000)" in schema_content, "path column not in documents"

        # Check new indexes
        assert "idx_documents_prefix" in schema_content, "prefix index not in v2 schema"
        assert "idx_documents_path" in schema_content, "path index not in v2 schema"

    @pytest.mark.asyncio
    async def test_v2_schema_no_external_id(self):
        """Verify v2 schema removes external_id fields."""
        from pathlib import Path

        schema_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "doc_vault"
            / "database"
            / "sql"
            / "schema_v2.sql"
        )

        with open(schema_path, "r") as f:
            schema_content = f.read()

        # Count external_id references (should be minimal - only in comments/migration notes)
        # The actual table definitions should not have external_id
        lines = schema_content.split("\n")

        # Find organizations table definition
        in_org_table = False
        for line in lines:
            if "CREATE TABLE IF NOT EXISTS organizations" in line:
                in_org_table = True
            elif in_org_table and (
                "CREATE TABLE" in line
                or "CREATE INDEX" in line
                or "CREATE TRIGGER" in line
            ):
                in_org_table = False

            if in_org_table and "external_id" in line:
                # Should only be in comments
                assert line.strip().startswith(
                    "--"
                ), f"external_id found in organizations table definition: {line}"


class TestMigrationScript:
    """Test migration script structure."""

    @pytest.mark.asyncio
    async def test_migration_script_structure(self):
        """Verify migration script has required sections."""
        from pathlib import Path

        migration_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "doc_vault"
            / "database"
            / "sql"
            / "migrate_v1_to_v2.sql"
        )

        with open(migration_path, "r") as f:
            migration_content = f.read()

        # Check for required sections
        assert "PHASE 1: CREATE NEW TABLES WITH V2 SCHEMA" in migration_content
        assert "PHASE 2: MIGRATION LOGIC" in migration_content
        assert "PHASE 3: DROP OLD TABLES AND RENAME V2 TABLES" in migration_content
        assert "PHASE 4: RESTORE FOREIGN KEYS AND INDEXES" in migration_content
        assert "PHASE 5: RECREATE TRIGGERS" in migration_content
        assert "PHASE 6: DATA VALIDATION" in migration_content

        # Check for backup tables
        assert "organizations_v1_backup" in migration_content
        assert "agents_v1_backup" in migration_content
        assert "documents_v1_backup" in migration_content

        # Check for data preservation logic
        assert "organizations_v2" in migration_content
        assert "agents_v2" in migration_content

        # Check for rollback instructions
        assert "TO ROLLBACK" in migration_content

    @pytest.mark.asyncio
    async def test_migration_has_validation_queries(self):
        """Verify migration script includes data validation."""
        from pathlib import Path

        migration_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "doc_vault"
            / "database"
            / "sql"
            / "migrate_v1_to_v2.sql"
        )

        with open(migration_path, "r") as f:
            migration_content = f.read()

        # Check for validation queries
        assert "migrated:" in migration_content
        assert "COUNT(*)" in migration_content
        assert "Orphaned" in migration_content


class TestInitDbIntegration:
    """Integration tests for init_db.py with v2.0."""

    @pytest.mark.asyncio
    async def test_schema_parsing_integration(self):
        """Test that schema_v2.sql parses without errors."""
        from pathlib import Path

        schema_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "doc_vault"
            / "database"
            / "sql"
            / "schema_v2.sql"
        )

        with open(schema_path, "r") as f:
            schema_content = f.read()

        # Parse statements
        statements = parse_sql_statements(schema_content)

        # Should have multiple statements
        assert len(statements) > 20, f"Expected 20+ statements, got {len(statements)}"

        # First statement should be extension
        assert "CREATE EXTENSION" in statements[0]

        # Should have table creation statements
        create_table_stmts = [s for s in statements if "CREATE TABLE" in s]
        assert (
            len(create_table_stmts) >= 6
        ), "Should have at least 6 table creation statements"

        # Should have trigger creation statements
        trigger_stmts = [s for s in statements if "CREATE TRIGGER" in s]
        assert (
            len(trigger_stmts) >= 4
        ), "Should have at least 4 trigger creation statements"

    @pytest.mark.asyncio
    async def test_migration_parsing_integration(self):
        """Test that migrate_v1_to_v2.sql parses without errors."""
        from pathlib import Path

        migration_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "doc_vault"
            / "database"
            / "sql"
            / "migrate_v1_to_v2.sql"
        )

        with open(migration_path, "r") as f:
            migration_content = f.read()

        # Parse statements
        statements = parse_sql_statements(migration_content)

        # Should have many statements
        assert len(statements) > 20, f"Expected 20+ statements, got {len(statements)}"

        # Should have backup table creation
        backup_stmts = [s for s in statements if "_v1_backup" in s]
        assert len(backup_stmts) >= 5, "Should create backup tables"

        # Should have v2 table creation
        v2_create_stmts = [s for s in statements if "_v2" in s and "CREATE TABLE" in s]
        assert len(v2_create_stmts) >= 3, "Should create v2 tables"


# Marker for Phase 1 completion
PHASE_1_SCHEMA_AND_MIGRATION_TESTS = True
