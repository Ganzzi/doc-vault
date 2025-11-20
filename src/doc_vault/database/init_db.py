"""
Database initialization script for DocVault.

This script initializes the PostgreSQL database with the required schema,
tables, indexes, and triggers for DocVault.

Supports:
- Fresh v2 database creation
- Automatic migration from v1 to v2
- Version detection and handling
"""

import asyncio
import logging
import sys
from pathlib import Path

from doc_vault.config import Config
from doc_vault.database.postgres_manager import PostgreSQLManager

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def detect_database_version(manager: PostgreSQLManager) -> str:
    """
    Detect the current database version.

    Returns:
        "v1" if v1 schema detected (has external_id columns)
        "v2" if v2 schema detected (no external_id, has prefix column)
        "empty" if no tables exist
    """
    try:
        # Check if organizations table exists and has external_id column
        query = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'organizations' AND column_name = 'external_id'
        """
        result = await manager.execute(query)
        rows = result.result() if result else []

        if rows:
            # Has external_id column -> v1 schema
            logger.info("Detected v1 schema (has external_id column)")
            return "v1"

        # Check if prefix column exists in documents
        query = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'documents' AND column_name = 'prefix'
        """
        result = await manager.execute(query)
        rows = result.result() if result else []

        if rows:
            # Has prefix column -> v2 schema
            logger.info("Detected v2 schema (has prefix column)")
            return "v2"

        # Check if any tables exist at all
        query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name IN ('organizations', 'agents', 'documents')
        """
        result = await manager.execute(query)
        rows = result.result() if result else []

        if rows:
            # Some tables exist but no recognized schema
            logger.warning("Detected unknown/partial schema")
            return "unknown"

        logger.info("Database is empty")
        return "empty"

    except Exception as e:
        logger.warning(f"Could not detect database version: {e}")
        return "empty"


def parse_sql_statements(sql_text: str) -> list[str]:
    """
    Parse SQL text into individual statements.

    Handles:
    - Single-line comments (--)
    - Multi-line comments (/* */)
    - Dollar-quoted strings ($$...$$) used in PostgreSQL functions
    - Standard statements ending with semicolon

    Args:
        sql_text: Raw SQL text

    Returns:
        List of individual SQL statements
    """
    statements = []
    current_statement = []
    in_multiline_comment = False
    in_dollar_quote = False

    for line in sql_text.splitlines():
        stripped_line = line.strip()

        # Skip empty lines and single-line comments (when not in dollar quote)
        if not in_dollar_quote and (
            not stripped_line or stripped_line.startswith("--")
        ):
            continue

        # Handle multi-line comments (when not in dollar quote)
        if not in_dollar_quote:
            if "/*" in stripped_line:
                in_multiline_comment = True
            if "*/" in stripped_line:
                in_multiline_comment = False
                continue
            if in_multiline_comment:
                continue

        # Check for dollar-quoted strings ($$...$$)
        if "$$" in stripped_line:
            # Count $$ occurrences to track in/out of dollar quotes
            dollar_count = stripped_line.count("$$")
            if dollar_count % 2 == 1:
                # Odd number: toggle state
                in_dollar_quote = not in_dollar_quote

        # Accumulate statement lines
        current_statement.append(line)

        # Check if statement ends (semicolon outside dollar quotes)
        if not in_dollar_quote and stripped_line.endswith(";"):
            statements.append("\n".join(current_statement))
            current_statement = []

    # Add any remaining statement
    if current_statement:
        statements.append("\n".join(current_statement))

    return [s.strip() for s in statements if s.strip()]


async def initialize_database(
    config: Config, schema_version: str = "v2", auto_migrate: bool = True
) -> bool:
    """
    Initialize the database with schema.

    Args:
        config: Database configuration
        schema_version: Target schema version ("v2" for new, "v1" for legacy)
        auto_migrate: Automatically migrate from v1 to v2 if needed

    Returns:
        True if successful, False otherwise
    """
    manager = PostgreSQLManager(config)

    try:
        # Initialize the connection pool
        logger.info("Initializing database connection pool...")
        await manager.initialize()

        # Verify connection
        logger.info("Verifying database connection...")
        if not await manager.verify_connection():
            logger.error("Failed to connect to database")
            return False

        # Detect current database version
        current_version = await detect_database_version(manager)
        logger.info(f"Current database version: {current_version}")

        # Handle migration if needed
        if current_version == "v1" and schema_version == "v2":
            if auto_migrate:
                logger.info("Migrating database from v1 to v2...")
                if not await run_migration_v1_to_v2(manager):
                    logger.error("Migration from v1 to v2 failed!")
                    return False
                logger.info("Migration completed successfully!")
                return True
            else:
                logger.error("Database is v1 but auto_migrate is disabled")
                return False

        if current_version == "v2" and schema_version == "v2":
            logger.info("Database is already v2, skipping initialization")
            return True

        if current_version == "empty" and schema_version == "v2":
            logger.info("Creating fresh v2 database...")
            return await create_v2_database(manager)

        if current_version == "unknown":
            logger.error("Database has unknown schema version, aborting")
            return False

        logger.error(
            f"Cannot initialize: current={current_version}, target={schema_version}"
        )
        return False

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False

    finally:
        # Clean up connection pool
        try:
            await manager.close()
        except Exception as e:
            logger.warning(f"Error closing database connection: {e}")


async def create_v2_database(manager: PostgreSQLManager) -> bool:
    """
    Create a fresh v2 database from schema_v2.sql.

    Args:
        manager: PostgreSQL manager instance

    Returns:
        True if successful, False otherwise
    """
    try:
        # Read v2 schema
        schema_path = Path(__file__).parent / "sql" / "schema_v2.sql"
        if not schema_path.exists():
            logger.error(f"Schema v2 file not found: {schema_path}")
            return False

        logger.info(f"Reading v2 schema from: {schema_path}")
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        # Parse and execute statements
        statements = parse_sql_statements(schema_sql)
        logger.info(f"Executing {len(statements)} SQL statements...")

        for i, statement in enumerate(statements, 1):
            if statement.strip():
                try:
                    await manager.execute(statement)
                    if i % 10 == 0 or i == len(statements):
                        logger.info(f"Executed {i}/{len(statements)} statements")
                except Exception as e:
                    logger.error(
                        f"Failed to execute statement {i}: {statement[:100]}..."
                    )
                    logger.error(f"Error: {e}")
                    return False

        logger.info("✅ v2 Database schema created successfully!")
        return True

    except Exception as e:
        logger.error(f"v2 Database creation failed: {e}")
        return False


async def run_migration_v1_to_v2(manager: PostgreSQLManager) -> bool:
    """
    Migrate database from v1 to v2 schema.

    Args:
        manager: PostgreSQL manager instance

    Returns:
        True if successful, False otherwise
    """
    try:
        # Read migration script
        migration_path = Path(__file__).parent / "sql" / "migrate_v1_to_v2.sql"
        if not migration_path.exists():
            logger.error(f"Migration script not found: {migration_path}")
            return False

        logger.info(f"Reading migration script from: {migration_path}")
        with open(migration_path, "r", encoding="utf-8") as f:
            migration_sql = f.read()

        # Parse and execute statements
        statements = parse_sql_statements(migration_sql)
        logger.info(f"Executing {len(statements)} migration statements...")

        for i, statement in enumerate(statements, 1):
            if statement.strip():
                try:
                    await manager.execute(statement)
                    if i % 10 == 0 or i == len(statements):
                        logger.info(
                            f"Executed {i}/{len(statements)} migration statements"
                        )
                except Exception as e:
                    logger.error(
                        f"Failed to execute migration statement {i}: {statement[:100]}..."
                    )
                    logger.error(f"Error: {e}")
                    logger.error(
                        "Migration failed! Database may be in inconsistent state."
                    )
                    logger.error("Restore from backup if necessary.")
                    return False

        logger.info("✅ Migration from v1 to v2 completed successfully!")
        return True

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


async def main() -> int:
    """Main entry point for database initialization."""
    try:
        # Load configuration from environment
        config = Config.from_env()
        logger.info(f"Initializing database: {config.postgres.db}")

        # Initialize v2 database with auto-migration from v1 if needed
        success = await initialize_database(
            config, schema_version="v2", auto_migrate=True
        )

        if success:
            logger.info("✅ Database initialization completed successfully!")
            return 0
        else:
            logger.error("❌ Database initialization failed!")
            return 1

    except Exception as e:
        logger.error(f"❌ Unexpected error during database initialization: {e}")
        return 1


if __name__ == "__main__":
    # Run the async main function
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
