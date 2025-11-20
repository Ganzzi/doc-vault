#!/usr/bin/env python3
"""
Check what tables exist in the database.
"""
import asyncio
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


async def main():
    """Check database tables."""
    try:
        from doc_vault.database.postgres_manager import PostgreSQLManager
        from doc_vault.config import Config

        m = PostgreSQLManager(Config())
        await m.initialize()

        # Check tables
        query_result = await m.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"
        )
        rows = query_result.result() if query_result else []
        print("Tables in public schema:")
        for row in rows:
            print(f"  - {row}")

        await m.close()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
