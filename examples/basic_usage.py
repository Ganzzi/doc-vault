"""
Basic usage example for DocVault SDK v2.2.

This example demonstrates the core functionality of the DocVault SDK:
- Organization and agent registration (with UUID org_id/agent_id)
- Document upload and download (including text content upload)
- Access control (unified set_permissions/get_permissions API with type-safe models)
- Document versioning (get_document_details with type-safe responses)
- Type-safe response models for all operations

Key v2.2 features:
- Type-safe response models (DocumentListResponse, SearchResponse, etc.)
- Smart text content upload (no temp files needed)
- Model-only permission API (PermissionGrant required)

Note: In v2.0+, org_id and agent_id for organizations and agents must be valid UUIDs.
"""

import asyncio
import tempfile
from pathlib import Path
import uuid
from typing import TYPE_CHECKING

from doc_vault import DocVaultSDK

if TYPE_CHECKING:
    from doc_vault.database.schemas import (
        DocumentListResponse,
        SearchResponse,
        DocumentDetails,
        PermissionListResponse,
    )


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

            # 5. List documents (v2.2 type-safe response)
            print("\nListing documents...")

            result = await vault.list_docs(
                organization_id=org_id,
                agent_id=agent1_id,
                limit=10,
            )
            # v2.2: Type-safe access via model attributes
            print(f"Found {result.pagination.total} document(s)")
            for doc in result.documents:
                print(f"   - {doc.name} (ID: {doc.id}, Status: {doc.status})")

            # 6. Search documents (v2.2 type-safe response)
            print("\nSearching documents...")

            search_results = await vault.search(
                query="sample document",
                organization_id=org_id,
                agent_id=agent1_id,
            )
            # v2.2: Type-safe access
            print(f"Search found {search_results.pagination.total} document(s)")
            for doc in search_results.documents:
                print(f"   - {doc.name} (ID: {doc.id})")

            # 7. Demonstrate access control (v2.2 type-safe API)
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
            # v2.2: Type-safe access
            print(f"   Agent 2 has {perms_result.total} permissions")

            # Grant READ permission to the second agent (v2.2: model-only)
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
            # v2.2: Type-safe access
            print(f"Agent 2 now has {perms_result.total} permission(s):")
            for acl in perms_result.permissions:
                print(f"   - {acl.permission}")

            # Second agent can now see the document in list_docs
            result = await vault.list_docs(agent_id=agent2_id, organization_id=org_id)
            # v2.2: Type-safe access
            print(f"Agent 2 can access {result.pagination.total} document(s)")

            # 8. Demonstrate versioning (v2.2 type-safe API)
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

                # Get document details with version history (v2.2 type-safe response)
                details = await vault.get_document_details(
                    document_id=document.id, agent_id=agent1_id, include_versions=True
                )
                # v2.2: Type-safe access
                print(f"Document has {details.version_count} version(s)")
                if details.versions:
                    for v in details.versions:
                        print(
                            f"   - Version {v.version_number}: {v.change_description or 'Initial upload'}"
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

            # 9. Demonstrate text content upload (v2.2 new feature)
            print("\nDemonstrating direct text upload (no temp file needed)...")

            text_doc = await vault.upload(
                file_input="This is direct text content uploaded without a temp file!",
                name="Quick Note",
                organization_id=org_id,
                agent_id=agent1_id,
                description="Direct text upload example",
                tags=["text", "quick", "v2.2"],
            )
            print(f"Text document uploaded: {text_doc.name} (ID: {text_doc.id})")
            print(f"   File size: {text_doc.file_size} bytes")

            # Download and verify
            text_content = await vault.download(
                document_id=text_doc.id, agent_id=agent1_id
            )
            print(f"   Content: {text_content.decode()}")

            print("\nDocVault SDK v2.2 demonstration completed successfully!")
            print("\nKey features demonstrated:")
            print("  - Organization and agent management with UUIDs")
            print("  - Document upload/download with multiple input types")
            print("  - Direct text content upload (no temp files) ⭐ NEW")
            print("  - Type-safe response models ⭐ NEW")
            print("  - Metadata management")
            print("  - Access control with type-safe PermissionGrant models")
            print("  - Document versioning with type-safe DocumentDetails")
            print("  - Search functionality with type-safe SearchResponse")

    finally:
        # Clean up temporary file
        Path(temp_file_path).unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main())
