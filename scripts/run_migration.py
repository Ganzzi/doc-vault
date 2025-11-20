#!/usr/bin/env python3
"""
Simple script to run database initialization and migration.
"""
import asyncio
import sys
import logging
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Run database initialization."""
    try:
        from doc_vault.database.init_db import initialize_database
        from doc_vault.config import Config

        logger.info("Starting database initialization...")

        # Use default config (loads from environment variables)
        config = Config()
        logger.info(
            f"Using PostgreSQL at {config.postgres_host}:{config.postgres_port}/{config.postgres_db}"
        )

        # Initialize database
        await initialize_database(config)
        logger.info("Database initialization completed successfully!")

    except Exception as e:
        logger.error(f"Error during database initialization: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
