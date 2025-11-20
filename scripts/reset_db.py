#!/usr/bin/env python3
"""
Reset the database by dropping all tables.
"""
import asyncio
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


async def main():
    """Drop all tables."""
    try:
        from doc_vault.database.postgres_manager import PostgreSQLManager
        from doc_vault.config import Config

        m = PostgreSQLManager(Config())
        await m.initialize()

        # Drop all tables
        await m.execute("DROP SCHEMA public CASCADE")
        await m.execute("CREATE SCHEMA public")

        print("Database reset: all tables dropped")

        await m.close()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
