"""
Versioning example for DocVault SDK.

This example demonstrates document versioning features:
- Creating multiple versions of documents
- Version history and metadata
- Restoring previous versions
- Version-specific downloads
- Version comparison
"""

import asyncio
import tempfile
from pathlib import Path

from doc_vault import DocVaultSDK


async def main():
    """Main versioning example function."""
    # Create temporary files for different versions
    temp_files = []

    try:
        # Create version 1 content
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(
                "Version 1: Initial draft of the project proposal.\n\nKey points:\n- Project scope\n- Timeline\n- Budget"
            )
            temp_files.append(f.name)

        # Create version 2 content
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(
                "Version 2: Updated project proposal with stakeholder feedback.\n\nKey points:\n- Expanded project scope\n- Revised timeline\n- Updated budget\n- Added risk assessment"
            )
            temp_files.append(f.name)

        # Create version 3 content
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(
                "Version 3: Final project proposal approved by management.\n\nKey points:\n- Final project scope\n- Approved timeline\n- Final budget\n- Risk mitigation plan\n- Success metrics"
            )
            temp_files.append(f.name)

        async with DocVaultSDK() as vault:
            print("🚀 DocVault SDK initialized for versioning demonstration!")

            # Setup: Create organization and agent
            print("\n📝 Setting up organization and agent...")

            org = await vault.register_organization(
                external_id="version-org-001",
                name="Version Control Inc",
                metadata={"industry": "software", "focus": "versioning"},
            )
            print(f"✅ Organization: {org.name}")

            agent = await vault.register_agent(
                external_id="author-001",
                organization_id="version-org-001",
                name="Document Author",
                email="author@version.com",
                agent_type="human",
                metadata={"role": "technical_writer", "department": "documentation"},
            )
            print(f"✅ Agent: {agent.name}")

            # Upload initial version (Version 1)
            print("\n📤 Uploading initial document version...")

            document = await vault.upload(
                file_path=temp_files[0],
                name="Project Proposal",
                organization_id="version-org-001",
                agent_id="author-001",
                description="Project proposal document with versioning demonstration",
                tags=["proposal", "project", "versioned"],
                metadata={"status": "draft", "version": "1.0"},
            )
            print(f"✅ Document uploaded: {document.name} (ID: {document.id})")
            print(f"   Initial version: {document.current_version}")

            # Check version history
            versions = await vault.get_versions(
                document_id=document.id, agent_id="author-001"
            )
            print(f"✅ Version history: {len(versions)} version(s)")
            for v in versions:
                print(
                    f"   - Version {v.version_number}: {v.change_description or 'Initial upload'}"
                )

            # Create Version 2 by replacing the document
            print("\n📝 Creating Version 2...")

            version2 = await vault.replace(
                document_id=document.id,
                file_path=temp_files[1],
                agent_id="author-001",
                change_description="Incorporated stakeholder feedback and expanded scope",
            )
            print(f"✅ Version 2 created: Version {version2.version_number}")
            print(f"   Change: {version2.change_description}")

            # Create Version 3
            print("\n📝 Creating Version 3...")

            version3 = await vault.replace(
                document_id=document.id,
                file_path=temp_files[2],
                agent_id="author-001",
                change_description="Final approval with management sign-off and risk mitigation",
            )
            print(f"✅ Version 3 created: Version {version3.version_number}")
            print(f"   Change: {version3.change_description}")

            # Get complete version history
            print("\n📚 Complete version history...")

            versions = await vault.get_versions(
                document_id=document.id, agent_id="author-001"
            )
            print(f"✅ Document now has {len(versions)} version(s):")

            for v in versions:
                print(f"\n   Version {v.version_number}:")
                print(f"     Created: {v.created_at}")
                print(f"     Size: {v.file_size} bytes")
                print(f"     Change: {v.change_description}")
                if hasattr(v, "metadata") and v.metadata:
                    print(f"     Metadata: {v.metadata}")

            # Download specific versions
            print("\n📥 Downloading specific versions...")

            for version_num in [1, 2, 3]:
                content = await vault.download(
                    document_id=document.id, agent_id="author-001", version=version_num
                )
                lines = content.decode().split("\n")
                first_line = lines[0] if lines else "Empty"
                print(
                    f"✅ Version {version_num}: {len(content)} bytes - '{first_line}'"
                )

            # Download latest version (default)
            print("\n📥 Downloading latest version...")

            latest_content = await vault.download(
                document_id=document.id, agent_id="author-001"
            )
            latest_lines = latest_content.decode().split("\n")
            latest_first_line = latest_lines[0] if latest_lines else "Empty"
            print(
                f"✅ Latest version: {len(latest_content)} bytes - '{latest_first_line}'"
            )

            # Demonstrate version restoration
            print("\n🔄 Demonstrating version restoration...")

            # Restore to Version 1
            restored_doc = await vault.restore_version(
                document_id=document.id,
                version_number=1,
                agent_id="author-001",
                change_description="Restoring to initial draft for review",
            )
            print(f"✅ Restored to Version {restored_doc.current_version}")
            print(f"   New version created: {restored_doc.current_version}")

            # Verify the restoration by downloading
            restored_content = await vault.download(
                document_id=document.id, agent_id="author-001"
            )
            restored_lines = restored_content.decode().split("\n")
            restored_first_line = restored_lines[0] if restored_lines else "Empty"
            print(f"✅ Restored content: '{restored_first_line}'")

            # Check final version history
            print("\n📚 Final version history after restoration...")

            final_versions = await vault.get_versions(
                document_id=document.id, agent_id="author-001"
            )
            print(f"✅ Document now has {len(final_versions)} version(s)")

            for v in final_versions:
                marker = (
                    " ← CURRENT" if v.version_number == document.current_version else ""
                )
                print(
                    f"   - Version {v.version_number}: {v.change_description}{marker}"
                )

            # Demonstrate version metadata updates
            print("\n✏️  Updating version metadata...")

            # Update the current version's metadata
            updated_doc = await vault.update_metadata(
                document_id=document.id,
                agent_id="author-001",
                metadata={
                    "status": "restored",
                    "restored_from": 1,
                    "restored_at": "2025-01-15",
                    "review_needed": True,
                },
            )
            print("✅ Updated document metadata for restored version")

            # Show document info with updated metadata (from the update_metadata call above)
            print(f"✅ Current document status: {updated_doc.status}")
            print(f"   Current version: {updated_doc.current_version}")
            if updated_doc.metadata:
                print(f"   Metadata: {updated_doc.metadata}")

            print("\n🎉 Versioning demonstration completed!")
            print("\nKey concepts demonstrated:")
            print("  ✅ Creating multiple document versions")
            print("  ✅ Version history tracking")
            print("  ✅ Version-specific downloads")
            print("  ✅ Restoring previous versions")
            print("  ✅ Change descriptions and metadata")
            print("  ✅ Version numbering and timestamps")

    finally:
        # Clean up temporary files
        for temp_file in temp_files:
            Path(temp_file).unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main())
