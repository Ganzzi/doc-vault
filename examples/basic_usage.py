"""
Basic usage example for DocVault SDK v2.0.

This example demonstrates the core functionality of the DocVault SDK:
- Organization and agent registration (with UUID org_id/agent_id)
- Document upload and download
- Access control (unified set_permissions/get_permissions API)
- Document versioning (get_document_details with include_versions)

Note: In v2.0, org_id and agent_id for organizations and agents must be valid UUIDs.
"""

import asyncio
import tempfile
from pathlib import Path
import uuid

from doc_vault import DocVaultSDK


async def main():
    """Main example function."""
    # Generate UUIDs for this example
    org_id = str(uuid.uuid4())
    agent1_id = str(uuid.uuid4())
    agent2_id = str(uuid.uuid4())

    # Create a temporary file for the example
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("This is a sample document for DocVault SDK demonstration.")
        temp_file_path = f.name

    try:
        # Initialize the SDK (uses environment variables from .env file)
        async with DocVaultSDK() as vault:
            print("DocVault SDK initialized successfully!")

            # 1. Register organization and agent
            print("\nRegistering organization and agent...")

            org = await vault.register_organization(
                org_id=org_id,
                metadata={
                    "display_name": "Example Corporation",
                    "industry": "technology",
                },
            )
            print(f"Organization registered: {org.id}")

            agent = await vault.register_agent(
                agent_id=agent1_id,
                organization_id=org_id,
                metadata={
                    "name": "John Doe",
                    "email": "john.doe@example.com",
                    "role": "administrator",
                    "department": "IT",
                },
            )
            print(f"Agent registered: {agent.id}")

            # 2. Upload a document
            print("\nUploading document...")

            document = await vault.upload(
                file_input=temp_file_path,
                name="Sample Document",
                organization_id=org_id,
                agent_id=agent1_id,
                description="A sample document for demonstration",
                tags=["sample", "demo", "documentation"],
                metadata={"version": "1.0", "confidential": False},
            )
            print(f"Document uploaded: {document.name} (ID: {document.id})")
            print(f"   File size: {document.file_size} bytes")
            print(f"   Current version: {document.current_version}")

            # 3. Download the document
            print("\nDownloading document...")

            content = await vault.download(document_id=document.id, agent_id=agent1_id)
            print(f"Document downloaded: {len(content)} bytes")
            print(f"   Content preview: {content.decode()[:50]}...")

            # 4. Update document metadata
            print("\nUpdating document metadata...")

            updated_doc = await vault.update_metadata(
                document_id=document.id,
                agent_id=agent1_id,
                name="Updated Sample Document",
                description="Updated description with more details",
                tags=["sample", "demo", "documentation", "updated"],
                metadata={
                    "version": "1.1",
                    "confidential": False,
                    "last_reviewed": "2025-01-15",
                },
            )
            print(f"Document metadata updated: {updated_doc.name}")

            # 5. List documents (v2.0 method)
            print("\nListing documents...")

            result = await vault.list_docs(
                organization_id=org_id,
                agent_id=agent1_id,
                limit=10,
            )
            documents = result.get("documents", [])
            print(f"Found {len(documents)} document(s)")
            for doc in documents:
                print(
                    f"   - {doc.get('name')} (ID: {doc.get('id')}, Status: {doc.get('status')})"
                )

            # 6. Search documents
            print("\nSearching documents...")

            search_results = await vault.search(
                query="sample document",
                organization_id=org_id,
                agent_id=agent1_id,
            )
            results = search_results.get("results", [])
            print(f"Search found {len(results)} document(s)")
            for doc in results:
                print(f"   - {doc.get('name')} (ID: {doc.get('id')})")

            # 7. Demonstrate access control (v2.0 API)
            print("\nDemonstrating access control...")

            # Register another agent
            other_agent = await vault.register_agent(
                agent_id=agent2_id,
                organization_id=org_id,
                metadata={
                    "name": "Jane Smith",
                    "email": "jane.smith@example.com",
                },
            )
            print(f"Second agent registered: {other_agent.id}")

            # Check initial permissions (should be empty for agent2)
            print("\nChecking Agent 2's initial permissions...")
            perms_result = await vault.get_permissions(
                document_id=document.id, agent_id=agent2_id
            )
            perms_list = perms_result.get("permissions", [])
            print(f"   Agent 2 has {len(perms_list)} permissions")

            # Grant READ permission to the second agent (v2.0 API)
            from doc_vault.database.schemas.permission import PermissionGrant

            await vault.set_permissions(
                document_id=document.id,
                permissions=[
                    PermissionGrant(
                        agent_id=agent2_id,
                        permission="READ",
                    ),
                ],
                granted_by=agent1_id,
            )
            print("Document shared with Agent 2 (READ permission)")

            # Now the second agent has access
            perms_result = await vault.get_permissions(
                document_id=document.id, agent_id=agent2_id
            )
            perms_list = perms_result.get("permissions", [])
            print(f"Agent 2 now has {len(perms_list)} permission(s):")
            for p in perms_list:
                print(f"   - {p['permission']}")

            # Second agent can now see the document in list_docs
            result = await vault.list_docs(agent_id=agent2_id, organization_id=org_id)
            accessible_docs = result.get("documents", [])
            print(f"Agent 2 can access {len(accessible_docs)} document(s)")

            # 8. Demonstrate versioning (v2.0 API)
            print("\nDemonstrating document versioning...")

            # Create a new version of the file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False
            ) as f:
                f.write(
                    "This is an updated version of the sample document with new content."
                )
                updated_file_path = f.name

            try:
                # Create new version (using upload with create_version=True)
                new_doc = await vault.upload(
                    file_input=updated_file_path,
                    name="Sample Document",  # Same name to trigger versioning
                    organization_id=org_id,
                    agent_id=agent1_id,
                    create_version=True,
                    change_description="Updated content with new information",
                )
                print(f"New version created: Version {new_doc.current_version}")

                # Get document details with version history (v2.0 API)
                details = await vault.get_document_details(
                    document_id=document.id, agent_id=agent1_id, include_versions=True
                )
                versions = details.get("versions", [])
                print(f"Document has {len(versions)} version(s)")
                for v in versions:
                    print(
                        f"   - Version {v.get('version_number')}: {v.get('change_description') or 'Initial upload'}"
                    )

                # Download a specific version
                old_content = await vault.download(
                    document_id=document.id,
                    agent_id=agent1_id,
                    version=1,  # Original version
                )
                print(f"Downloaded version 1: {len(old_content)} bytes")
                print(f"   Original content preview: {old_content.decode()[:50]}...")

            finally:
                Path(updated_file_path).unlink(missing_ok=True)

            print("\nDocVault SDK v2.0 demonstration completed successfully!")
            print("\nKey features demonstrated:")
            print("  - Organization and agent management with UUIDs")
            print("  - Document upload/download with multiple input types")
            print("  - Metadata management")
            print("  - Access control with set_permissions/get_permissions")
            print("  - Document versioning with get_document_details")
            print("  - Search functionality")

    finally:
        # Clean up temporary file
        Path(temp_file_path).unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main())
