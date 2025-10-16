"""
Basic usage example for DocVault SDK.

This example demonstrates the core functionality of the DocVault SDK:
- Organization and agent registration
- Document upload and download
- Access control (sharing and permissions)
- Document versioning
"""

import asyncio
import tempfile
from pathlib import Path

from doc_vault import DocVaultSDK


async def main():
    """Main example function."""
    # Create a temporary file for the example
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("This is a sample document for DocVault SDK demonstration.")
        temp_file_path = f.name

    try:
        # Initialize the SDK (uses environment variables from .env file)
        async with DocVaultSDK() as vault:
            print("🚀 DocVault SDK initialized successfully!")

            # 1. Register organization and agent
            print("\n📝 Registering organization and agent...")

            org = await vault.register_organization(
                external_id="example-org-001",
                name="Example Corporation",
                metadata={"industry": "technology", "size": "startup"},
            )
            print(f"✅ Organization registered: {org.name} (ID: {org.id})")

            agent = await vault.register_agent(
                external_id="example-agent-001",
                organization_id="example-org-001",
                name="John Doe",
                email="john.doe@example.com",
                agent_type="human",
                metadata={"role": "developer", "department": "engineering"},
            )
            print(f"✅ Agent registered: {agent.name} (ID: {agent.id})")

            # 2. Upload a document
            print("\n📤 Uploading document...")

            document = await vault.upload(
                file_path=temp_file_path,
                name="Sample Document",
                organization_id="example-org-001",
                agent_id="example-agent-001",
                description="A sample document for demonstration",
                tags=["sample", "demo", "documentation"],
                metadata={"version": "1.0", "confidential": False},
            )
            print(f"✅ Document uploaded: {document.name} (ID: {document.id})")
            print(f"   File size: {document.file_size} bytes")
            print(f"   Current version: {document.current_version}")

            # 3. Download the document
            print("\n📥 Downloading document...")

            content = await vault.download(
                document_id=document.id, agent_id="example-agent-001"
            )
            print(f"✅ Document downloaded: {len(content)} bytes")
            print(f"   Content preview: {content.decode()[:50]}...")

            # 4. Update document metadata
            print("\n✏️  Updating document metadata...")

            updated_doc = await vault.update_metadata(
                document_id=document.id,
                agent_id="example-agent-001",
                name="Updated Sample Document",
                description="Updated description with more details",
                tags=["sample", "demo", "documentation", "updated"],
                metadata={
                    "version": "1.1",
                    "confidential": False,
                    "last_reviewed": "2025-01-15",
                },
            )
            print(f"✅ Document metadata updated: {updated_doc.name}")

            # 5. List documents
            print("\n📋 Listing documents...")

            documents = await vault.list_documents(
                organization_id="example-org-001",
                agent_id="example-agent-001",
                limit=10,
            )
            print(f"✅ Found {len(documents)} document(s)")
            for doc in documents:
                print(f"   - {doc.name} (ID: {doc.id}, Status: {doc.status})")

            # 6. Search documents
            print("\n🔍 Searching documents...")

            search_results = await vault.search(
                query="sample document",
                organization_id="example-org-001",
                agent_id="example-agent-001",
            )
            print(f"✅ Search found {len(search_results)} document(s)")
            for doc in search_results:
                print(f"   - {doc.name} (ID: {doc.id})")

            # 7. Demonstrate access control
            print("\n🔐 Demonstrating access control...")

            # Register another agent
            other_agent = await vault.register_agent(
                external_id="example-agent-002",
                organization_id="example-org-001",
                name="Jane Smith",
                email="jane.smith@example.com",
                agent_type="human",
            )
            print(f"✅ Second agent registered: {other_agent.name}")

            # Initially, the second agent cannot access the document
            has_access = await vault.check_permission(
                document_id=document.id, agent_id="example-agent-002", permission="READ"
            )
            print(f"❌ Agent 2 has READ permission: {has_access}")

            # Share the document with the second agent
            await vault.share(
                document_id=document.id,
                agent_id="example-agent-002",
                permission="READ",
                granted_by="example-agent-001",
            )
            print("✅ Document shared with Agent 2 (READ permission)")

            # Now the second agent can access it
            has_access = await vault.check_permission(
                document_id=document.id, agent_id="example-agent-002", permission="READ"
            )
            print(f"✅ Agent 2 has READ permission: {has_access}")

            # Second agent can now see the document in their accessible list
            accessible_docs = await vault.list_accessible_documents(
                agent_id="example-agent-002", organization_id="example-org-001"
            )
            print(f"✅ Agent 2 can access {len(accessible_docs)} document(s)")

            # 8. Demonstrate versioning
            print("\n📚 Demonstrating document versioning...")

            # Create a new version of the file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False
            ) as f:
                f.write(
                    "This is an updated version of the sample document with new content."
                )
                updated_file_path = f.name

            try:
                # Replace the document (creates version 2)
                new_version = await vault.replace(
                    document_id=document.id,
                    file_path=updated_file_path,
                    agent_id="example-agent-001",
                    change_description="Updated content with new information",
                )
                print(f"✅ New version created: Version {new_version.version_number}")

                # List all versions
                versions = await vault.get_versions(
                    document_id=document.id, agent_id="example-agent-001"
                )
                print(f"✅ Document has {len(versions)} version(s)")
                for v in versions:
                    print(
                        f"   - Version {v.version_number}: {v.change_description or 'Initial upload'}"
                    )

                # Download a specific version
                old_content = await vault.download(
                    document_id=document.id,
                    agent_id="example-agent-001",
                    version=1,  # Original version
                )
                print(f"✅ Downloaded version 1: {len(old_content)} bytes")
                print(f"   Original content preview: {old_content.decode()[:50]}...")

            finally:
                Path(updated_file_path).unlink(missing_ok=True)

            print("\n🎉 DocVault SDK demonstration completed successfully!")
            print("\nKey features demonstrated:")
            print("  ✅ Organization and agent management")
            print("  ✅ Document upload/download")
            print("  ✅ Metadata management")
            print("  ✅ Access control and sharing")
            print("  ✅ Document versioning")
            print("  ✅ Search functionality")

    finally:
        # Clean up temporary file
        Path(temp_file_path).unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main())
