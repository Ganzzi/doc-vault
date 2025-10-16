"""
Access control example for DocVault SDK.

This example demonstrates advanced access control features:
- Document sharing with different permission levels
- Permission checking and validation
- Managing access lists
- Revoking permissions
"""

import asyncio
import tempfile
from pathlib import Path

from doc_vault import DocVaultSDK


async def main():
    """Main access control example function."""
    # Create a temporary file for the example
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("This is a confidential document for access control demonstration.")
        temp_file_path = f.name

    try:
        async with DocVaultSDK() as vault:
            print("🚀 DocVault SDK initialized for access control demonstration!")

            # Setup: Create organization and multiple agents
            print("\n📝 Setting up organization and agents...")

            org = await vault.register_organization(
                external_id="security-org-001",
                name="Security Corp",
                metadata={"industry": "security", "classification": "confidential"},
            )
            print(f"✅ Organization: {org.name}")

            # Create multiple agents with different roles
            admin_agent = await vault.register_agent(
                external_id="admin-001",
                organization_id="security-org-001",
                name="Admin User",
                email="admin@security.com",
                agent_type="human",
                metadata={"role": "administrator", "clearance": "top-secret"},
            )
            print(f"✅ Admin agent: {admin_agent.name}")

            manager_agent = await vault.register_agent(
                external_id="manager-001",
                organization_id="security-org-001",
                name="Manager User",
                email="manager@security.com",
                agent_type="human",
                metadata={"role": "manager", "clearance": "secret"},
            )
            print(f"✅ Manager agent: {manager_agent.name}")

            employee_agent = await vault.register_agent(
                external_id="employee-001",
                organization_id="security-org-001",
                name="Employee User",
                email="employee@security.com",
                agent_type="human",
                metadata={"role": "employee", "clearance": "confidential"},
            )
            print(f"✅ Employee agent: {employee_agent.name}")

            # Upload a confidential document
            print("\n📤 Uploading confidential document...")

            document = await vault.upload(
                file_path=temp_file_path,
                name="Confidential Security Report",
                organization_id="security-org-001",
                agent_id="admin-001",
                description="Highly confidential security assessment report",
                tags=["confidential", "security", "report"],
                metadata={
                    "classification": "top-secret",
                    "department": "security",
                    "expires": "2026-12-31",
                },
            )
            print(f"✅ Document uploaded: {document.name} (ID: {document.id})")

            # Demonstrate permission levels
            print("\n🔐 Demonstrating permission levels...")

            # Initially, no one except the owner has access
            print("\n--- Initial Access Check ---")
            permissions_to_check = ["READ", "WRITE", "DELETE", "SHARE"]

            for agent_id, agent_name in [
                ("manager-001", "Manager"),
                ("employee-001", "Employee"),
            ]:
                print(f"\n{agent_name} permissions:")
                for perm in permissions_to_check:
                    has_perm = await vault.check_permission(
                        document_id=document.id, agent_id=agent_id, permission=perm
                    )
                    status = "✅" if has_perm else "❌"
                    print(f"  {perm}: {status}")

            # Share with different permission levels
            print("\n--- Sharing Document ---")

            # Manager gets READ and WRITE permissions
            await vault.share(
                document_id=document.id,
                agent_id="manager-001",
                permission="WRITE",  # WRITE implies READ
                granted_by="admin-001",
            )
            print("✅ Shared with Manager (WRITE permission)")

            # Employee gets only READ permission
            await vault.share(
                document_id=document.id,
                agent_id="employee-001",
                permission="READ",
                granted_by="admin-001",
            )
            print("✅ Shared with Employee (READ permission)")

            # Check permissions after sharing
            print("\n--- Access Check After Sharing ---")

            for agent_id, agent_name in [
                ("manager-001", "Manager"),
                ("employee-001", "Employee"),
            ]:
                print(f"\n{agent_name} permissions:")
                for perm in permissions_to_check:
                    has_perm = await vault.check_permission(
                        document_id=document.id, agent_id=agent_id, permission=perm
                    )
                    status = "✅" if has_perm else "❌"
                    print(f"  {perm}: {status}")

            # Demonstrate what each agent can do
            print("\n--- Testing Actual Access ---")

            # Manager can update metadata (WRITE permission)
            print("\nManager updating document metadata...")
            try:
                updated_doc = await vault.update_metadata(
                    document_id=document.id,
                    agent_id="manager-001",
                    name="Confidential Security Report - Updated",
                    description="Updated security assessment report with new findings",
                )
                print("✅ Manager successfully updated metadata")
            except Exception as e:
                print(f"❌ Manager failed to update metadata: {e}")

            # Employee can read the document
            print("\nEmployee downloading document...")
            try:
                content = await vault.download(
                    document_id=document.id, agent_id="employee-001"
                )
                print(f"✅ Employee successfully downloaded {len(content)} bytes")
            except Exception as e:
                print(f"❌ Employee failed to download: {e}")

            # Employee cannot update metadata (no WRITE permission)
            print("\nEmployee attempting to update metadata...")
            try:
                await vault.update_metadata(
                    document_id=document.id,
                    agent_id="employee-001",
                    name="Confidential Security Report - Employee Edit",
                )
                print("❌ Employee unexpectedly succeeded in updating metadata")
            except Exception as e:
                print(f"✅ Employee correctly denied metadata update: {e}")

            # List accessible documents for each agent
            print("\n--- Accessible Documents ---")

            for agent_id, agent_name in [
                ("admin-001", "Admin"),
                ("manager-001", "Manager"),
                ("employee-001", "Employee"),
            ]:
                accessible = await vault.list_accessible_documents(
                    agent_id=agent_id, organization_id="security-org-001"
                )
                print(f"{agent_name} can access {len(accessible)} document(s)")

            # Demonstrate revoking permissions
            print("\n--- Revoking Permissions ---")

            # Revoke employee's access
            await vault.revoke(
                document_id=document.id,
                agent_id="employee-001",
                permission="READ",
                revoked_by="admin-001",
            )
            print("✅ Revoked Employee's access")

            # Check that employee no longer has access
            has_access = await vault.check_permission(
                document_id=document.id, agent_id="employee-001", permission="READ"
            )
            print(f"Employee still has READ access: {'✅' if has_access else '❌'}")

            # Employee can no longer access the document
            try:
                await vault.download(document_id=document.id, agent_id="employee-001")
                print("❌ Employee unexpectedly can still download")
            except Exception as e:
                print(f"✅ Employee correctly denied access: {e}")

            # Show final access list
            print("\n--- Final Access Summary ---")

            # Get all permissions for the document
            permissions = await vault.get_document_permissions(
                document_id=document.id, agent_id="admin-001"
            )
            print(f"Document has {len(permissions)} permission entries:")
            for perm in permissions:
                print(f"  - Agent {perm.agent_id}: {perm.permission}")

            print("\n🎉 Access control demonstration completed!")
            print("\nKey concepts demonstrated:")
            print("  ✅ Permission levels (READ, WRITE, DELETE, SHARE)")
            print("  ✅ Sharing documents with specific permissions")
            print("  ✅ Permission validation and enforcement")
            print("  ✅ Revoking access")
            print("  ✅ Listing accessible documents")
            print("  ✅ Role-based access control patterns")

    finally:
        # Clean up temporary file
        Path(temp_file_path).unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main())
