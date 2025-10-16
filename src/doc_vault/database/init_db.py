"""
Database initialization script for DocVault.

This script initializes the PostgreSQL database with the required schema,
tables, indexes, and triggers for DocVault.
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


async def initialize_database(config: Config) -> bool:
    """
    Initialize the database with schema.

    Args:
        config: Database configuration

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

        # Read and execute schema SQL
        schema_path = Path(__file__).parent / "sql" / "schema.sql"
        if not schema_path.exists():
            logger.error(f"Schema file not found: {schema_path}")
            return False

        logger.info(f"Reading schema from: {schema_path}")
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        # Split SQL into individual statements (basic approach)
        # Note: This is a simple splitter that may not handle all edge cases
        statements = []
        current_statement = []
        in_multiline_comment = False

        for line in schema_sql.splitlines():
            line = line.strip()

            # Skip empty lines and single-line comments
            if not line or line.startswith("--"):
                continue

            # Handle multi-line comments (basic)
            if "/*" in line:
                in_multiline_comment = True
            if "*/" in line:
                in_multiline_comment = False
                continue
            if in_multiline_comment:
                continue

            # Accumulate statement lines
            current_statement.append(line)

            # Check if statement ends
            if line.endswith(";"):
                statements.append(" ".join(current_statement))
                current_statement = []

        # Execute each statement
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

        logger.info("Database schema initialized successfully!")
        return True

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False

    finally:
        # Clean up connection pool
        try:
            await manager.close()
        except Exception as e:
            logger.warning(f"Error closing database connection: {e}")


async def main() -> int:
    """Main entry point for database initialization."""
    try:
        # Load configuration from environment
        config = Config.from_env()
        logger.info(f"Initializing database: {config.postgres.db}")

        # Initialize database
        success = await initialize_database(config)

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
