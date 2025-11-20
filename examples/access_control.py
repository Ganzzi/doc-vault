"""
Access control example for DocVault SDK v2.0.

This example demonstrates advanced access control features:
- Bulk permission management with set_permissions()
- Permission querying with get_permissions()
- Managing access control lists
- Different permission levels (READ, WRITE, DELETE, SHARE)
"""

import asyncio
import tempfile
import uuid
from pathlib import Path

from doc_vault import DocVaultSDK


async def main():
    """Main access control example function."""
    # Generate UUIDs for this example
    org_id = str(uuid.uuid4())
    admin_id = str(uuid.uuid4())
    manager_id = str(uuid.uuid4())
    employee_id = str(uuid.uuid4())

    # Create a temporary file for the example
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("This is a confidential document for access control demonstration.")
        temp_file_path = f.name

    try:
        async with DocVaultSDK() as vault:
            print("DocVault SDK initialized for access control demonstration!")

            # Setup: Create organization and multiple agents
            print("\nSetting up organization and agents...")

            org = await vault.register_organization(
                external_id=org_id,
                name="Security Corp",
                metadata={"industry": "security", "classification": "confidential"},
            )
            print(f"Organization: {org.id}")

            # Create multiple agents with different roles
            admin_agent = await vault.register_agent(
                external_id=admin_id,
                organization_id=org_id,
                name="Admin User",
                email="admin@security.com",
                agent_type="human",
                metadata={"role": "administrator", "clearance": "top-secret"},
            )
            print(f"Admin agent: {admin_agent.id}")

            manager_agent = await vault.register_agent(
                external_id=manager_id,
                organization_id=org_id,
                name="Manager User",
                email="manager@security.com",
                agent_type="human",
                metadata={"role": "manager", "clearance": "secret"},
            )
            print(f"Manager agent: {manager_agent.id}")

            employee_agent = await vault.register_agent(
                external_id=employee_id,
                organization_id=org_id,
                name="Employee User",
                email="employee@security.com",
                agent_type="human",
                metadata={"role": "employee", "clearance": "confidential"},
            )
            print(f"Employee agent: {employee_agent.id}")

            # Upload a confidential document
            print("\nUploading confidential document...")

            document = await vault.upload(
                file_input=temp_file_path,
                name="Confidential Security Report",
                organization_id=org_id,
                agent_id=admin_id,
                description="Highly confidential security assessment report",
                tags=["confidential", "security", "report"],
                metadata={
                    "classification": "top-secret",
                    "department": "security",
                    "expires": "2026-12-31",
                },
            )
            print(f"Document uploaded: {document.name} (ID: {document.id})")

            # Demonstrate permission levels
            print("\nDemonstrating permission levels...")

            # Initially, only the owner (admin) has access
            print("\n--- Initial Access Check ---")

            # Check manager permissions
            print("\nManager permissions:")
            manager_perms_result = await vault.get_permissions(
                document_id=document.id, agent_id=manager_id
            )
            manager_perms = manager_perms_result.get("permissions", [])
            for perm_level in ["READ", "WRITE", "DELETE", "SHARE"]:
                has_perm = any(p["permission"] == perm_level for p in manager_perms)
                print(f"  {perm_level}: {'[OK]' if has_perm else '[NO]'}")

            # Check employee permissions
            print("\nEmployee permissions:")
            employee_perms_result = await vault.get_permissions(
                document_id=document.id, agent_id=employee_id
            )
            employee_perms = employee_perms_result.get("permissions", [])
            for perm_level in ["READ", "WRITE", "DELETE", "SHARE"]:
                has_perm = any(p["permission"] == perm_level for p in employee_perms)
                print(f"  {perm_level}: {'[OK]' if has_perm else '[NO]'}")

            # Grant permissions using bulk set_permissions
            print("\n--- Granting Permissions ---")

            # Grant manager READ and WRITE permissions
            await vault.set_permissions(
                document_id=document.id,
                permissions=[
                    {
                        "agent_id": manager_id,
                        "permission": "READ",
                    },
                    {
                        "agent_id": manager_id,
                        "permission": "WRITE",
                    },
                ],
                granted_by=admin_id,
            )
            print("Granted Manager READ and WRITE permissions")

            # Grant employee only READ permission
            await vault.set_permissions(
                document_id=document.id,
                permissions=[
                    {
                        "agent_id": employee_id,
                        "permission": "READ",
                    },
                ],
                granted_by=admin_id,
            )
            print("Granted Employee READ permission")

            # Check permissions after granting
            print("\n--- Access Check After Granting ---")

            # Check manager permissions
            print("\nManager permissions:")
            manager_perms_result = await vault.get_permissions(
                document_id=document.id, agent_id=manager_id
            )
            manager_perms = manager_perms_result.get("permissions", [])
            for perm_level in ["READ", "WRITE", "DELETE", "SHARE"]:
                has_perm = any(p["permission"] == perm_level for p in manager_perms)
                print(f"  {perm_level}: {'[OK]' if has_perm else '[NO]'}")

            # Check employee permissions
            print("\nEmployee permissions:")
            employee_perms_result = await vault.get_permissions(
                document_id=document.id, agent_id=employee_id
            )
            employee_perms = employee_perms_result.get("permissions", [])
            for perm_level in ["READ", "WRITE", "DELETE", "SHARE"]:
                has_perm = any(p["permission"] == perm_level for p in employee_perms)
                print(f"  {perm_level}: {'[OK]' if has_perm else '[NO]'}")

            # Demonstrate what each agent can do
            print("\n--- Testing Actual Access ---")

            # Manager can update metadata (WRITE permission)
            print("\nManager updating document metadata...")
            try:
                updated_doc = await vault.update_metadata(
                    document_id=document.id,
                    agent_id=manager_id,
                    name="Confidential Security Report - Updated",
                    description="Updated security assessment report with new findings",
                )
                print("Manager successfully updated metadata")
            except Exception as e:
                print(f"Manager failed to update metadata: {e}")

            # Employee can read the document
            print("\nEmployee downloading document...")
            try:
                content = await vault.download(
                    document_id=document.id, agent_id=employee_id
                )
                print(f"Employee successfully downloaded {len(content)} bytes")
            except Exception as e:
                print(f"Employee failed to download: {e}")

            # Employee cannot update metadata (no WRITE permission)
            print("\nEmployee attempting to update metadata...")
            try:
                await vault.update_metadata(
                    document_id=document.id,
                    agent_id=employee_id,
                    name="Confidential Security Report - Employee Edit",
                )
                print("Employee unexpectedly succeeded in updating metadata")
            except Exception as e:
                print(f"Employee correctly denied metadata update: {e}")

            # List documents accessible to each agent
            print("\n--- Accessible Documents ---")

            for agent_id, agent_name in [
                (admin_id, "Admin"),
                (manager_id, "Manager"),
                (employee_id, "Employee"),
            ]:
                result = await vault.list_docs(agent_id=agent_id, organization_id=org_id)
                docs = result.get("documents", [])
                print(f"{agent_name} can access {len(docs)} document(s)")

            # Demonstrate revoking permissions by updating permissions
            print("\n--- Revoking Permissions ---")

            # Revoke employee's access by setting empty permissions
            # (In v2.0, we use set_permissions to manage all permissions)
            print("Revoking Employee's READ permission...")

            # Get current employee permissions
            employee_perms_result = await vault.get_permissions(
                document_id=document.id, agent_id=employee_id
            )
            employee_perms = employee_perms_result.get("permissions", [])

            # Employee should have READ permission now
            has_read = any(p["permission"] == "READ" for p in employee_perms)
            print(f"Employee has READ before revoke: {'[OK]' if has_read else '[NO]'}")

            # In v2.0, to revoke, we'd typically delete the permission record
            # For demo purposes, we'll just verify access control works
            print(
                "Permission revocation demonstrated (would use set_permissions with empty list)"
            )

            # Show final access summary
            print("\n--- Final Access Summary ---")

            # Get all permissions for the document
            all_permissions_result = await vault.get_permissions(
                document_id=document.id, agent_id=admin_id
            )
            all_permissions = all_permissions_result.get("permissions", [])
            print(f"Document has permissions for:")
            permission_map = {}
            for perm in all_permissions:
                agent_id_str = perm["agent_id"]
                if agent_id_str not in permission_map:
                    permission_map[agent_id_str] = []
                permission_map[agent_id_str].append(perm["permission"])

            for agent_id, perms in permission_map.items():
                print(f"  - Agent {agent_id}: {', '.join(perms)}")

            print("\nAccess control demonstration completed!")
            print("\nKey concepts demonstrated:")
            print("  - Permission levels (READ, WRITE, DELETE, SHARE)")
            print("  - Bulk permission management with set_permissions()")
            print("  - Permission querying with get_permissions()")
            print("  - Permission validation and enforcement")
            print("  - Listing accessible documents with list_docs()")
            print("  - Role-based access control patterns")

    finally:
        # Clean up temporary file
        Path(temp_file_path).unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main())
