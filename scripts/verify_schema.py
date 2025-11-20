#!/usr/bin/env python3
"""
Verify v2 schema has correct columns.
"""
import asyncio
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


async def main():
    """Verify schema."""
    try:
        from doc_vault.database.postgres_manager import PostgreSQLManager
        from doc_vault.config import Config

        m = PostgreSQLManager(Config())
        await m.initialize()

        # Check organizations table (should NOT have external_id or name)
        print("=== ORGANIZATIONS TABLE ===")
        result = await m.execute(
            "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'organizations' ORDER BY ordinal_position"
        )
        for row in result.result():
            print(f"  {row['column_name']}: {row['data_type']}")

        # Check agents table (should NOT have external_id, name, email, agent_type)
        print("\n=== AGENTS TABLE ===")
        result = await m.execute(
            "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'agents' ORDER BY ordinal_position"
        )
        for row in result.result():
            print(f"  {row['column_name']}: {row['data_type']}")

        # Check documents table (should have prefix and path)
        print("\n=== DOCUMENTS TABLE ===")
        result = await m.execute(
            "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'documents' ORDER BY ordinal_position"
        )
        for row in result.result():
            print(f"  {row['column_name']}: {row['data_type']}")

        # Check indexes
        print("\n=== INDEXES ===")
        result = await m.execute(
            "SELECT indexname FROM pg_indexes WHERE schemaname = 'public' ORDER BY indexname"
        )
        for row in result.result():
            print(f"  {row['indexname']}")

        await m.close()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
