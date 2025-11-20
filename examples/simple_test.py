"""
Simple test to verify DocVault v2.0 SDK is working.

This uses proper UUIDs for organizations and agents as required by v2.0.
"""

import asyncio
import uuid
import tempfile
from pathlib import Path

from doc_vault import DocVaultSDK


async def main():
    """Simple test function."""
    print("DocVault v2.0 SDK Simple Test\n")

    # Generate UUIDs for v2.0
    org_uuid = str(uuid.uuid4())
    agent_uuid = str(uuid.uuid4())

    print(f"Generated UUIDs:")
    print(f"   Org UUID:   {org_uuid}")
    print(f"   Agent UUID: {agent_uuid}\n")

    # Create temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Test document content for v2.0 SDK")
        temp_file = f.name

    try:
        async with DocVaultSDK() as vault:
            print("SDK initialized\n")

            # Register organization
            print("1. Registering organization...")
            org = await vault.register_organization(
                external_id=org_uuid,
                metadata={"test": True},
            )
            print(f"   Organization ID: {org.id}\n")

            # Register agent
            print("2. Registering agent...")
            agent = await vault.register_agent(
                external_id=agent_uuid,
                organization_id=org_uuid,
                metadata={"role": "tester"},
            )
            print(f"   Agent ID: {agent.id}\n")

            # Upload document
            print("3. Uploading document...")
            doc = await vault.upload(
                file_input=temp_file,
                name="Test Document",
                organization_id=org_uuid,
                agent_id=agent_uuid,
                description="Test document",
                tags=["test"],
                metadata={"version": "1.0"},
            )
            print(f"   Document ID: {doc.id}")
            print(f"   File size: {doc.file_size} bytes\n")

            # List documents
            print("4. Listing documents...")
            result = await vault.list_docs(
                organization_id=org_uuid,
                agent_id=agent_uuid,
            )
            docs = result.get("documents", [])
            print(f"   Found {len(docs)} document(s)\n")

            # Download document
            print("5. Downloading document...")
            content = await vault.download(
                document_id=doc.id,
                agent_id=agent_uuid,
            )
            print(f"   Downloaded {len(content)} bytes")
            print(f"   Content: {content.decode()}\n")

            print("All tests passed! v2.0 SDK is working correctly.")

    finally:
        Path(temp_file).unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main())
