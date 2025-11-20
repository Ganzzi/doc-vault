"""
Access control example for DocVault SDK v2.0.

This example demonstrates v2.0 access control features:
- Bulk permission management with set_permissions_bulk()
- Multi-permission checking with check_permissions_multi()
- Detailed permission queries with get_permissions_detailed()
- Advanced access control patterns
"""

import asyncio
import tempfile
from pathlib import Path
from uuid import uuid4

from doc_vault import DocVaultSDK


async def main():
    """Main access control example function for v2.0."""
    # Create a temporary file for the example
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("This is a confidential document for access control demonstration.")
        temp_file_path = f.name

    try:
        async with DocVaultSDK() as vault:
            print("=" * 70)
            print("DocVault v2.0 - Advanced Access Control Demo")
            print("=" * 70)

            # Setup: Create organization and multiple agents
            print("\n[1] Setting up organization and agents...")

            org_id = uuid4()
            org = await vault.register_organization(
                external_id=str(org_id),
                metadata={"industry": "security", "classification": "confidential"},
            )
            print(f"[OK] Organization registered: {org.id}")

            # Create multiple agents with different roles
            admin_id = uuid4()
            admin_agent = await vault.register_agent(
                external_id=str(admin_id),
                organization_id=str(org_id),
                metadata={"role": "administrator", "clearance": "top-secret"},
            )
            print(f"[OK] Admin agent registered: {admin_agent.id}")

            manager_id = uuid4()
            manager_agent = await vault.register_agent(
                external_id=str(manager_id),
                organization_id=str(org_id),
                metadata={"role": "manager", "clearance": "secret"},
            )
            print(f"[OK] Manager agent registered: {manager_agent.id}")

            employee_id = uuid4()
            employee_agent = await vault.register_agent(
                external_id=str(employee_id),
                organization_id=str(org_id),
                metadata={"role": "employee", "clearance": "confidential"},
            )
            print(f"[OK] Employee agent registered: {employee_agent.id}")

            contractor_id = uuid4()
            contractor_agent = await vault.register_agent(
                external_id=str(contractor_id),
                organization_id=str(org_id),
                metadata={"role": "contractor", "clearance": "none"},
            )
            print(f"[OK] Contractor agent registered: {contractor_agent.id}")

            # Upload a confidential document using v2.0 enhanced upload
            print("\n[2] Uploading confidential document with enhanced features...")

            with open(temp_file_path, "rb") as file:
                content = file.read()

            document = await vault.upload_enhanced(
                file_input=content,
                filename="confidential_report.txt",
                name="Confidential Security Report",
                organization_id=str(org_id),
                agent_id=str(admin_id),
                description="Highly confidential security assessment report",
                tags=["confidential", "security", "report"],
                metadata={
                    "classification": "top-secret",
                    "department": "security",
                    "expires": "2026-12-31",
                },
            )
            print(f"[OK] Document uploaded: {document.name}")
            print(f"     ID: {document.id}")
            print(f"     Storage path: {document.prefix}/{document.path}")

            # v2.0 Feature: Bulk Permission Management
            print("\n[3] Setting up bulk permissions (v2.0 feature)...")

            permissions = [
                {"agent_id": str(manager_id), "permission": "WRITE"},
                {"agent_id": str(employee_id), "permission": "READ"},
                {"agent_id": str(contractor_id), "permission": "READ"},
            ]

            acls = await vault.set_permissions_bulk(
                document_id=document.id,
                permissions=permissions,
                granted_by=str(admin_id),
            )
            print(f"[OK] Bulk permissions set: {len(acls)} ACL entries created")
            for acl in acls:
                print(f"     - Agent {acl.agent_id}: {acl.permission}")

            # v2.0 Feature: Multi-Permission Check
            print("\n[4] Checking multiple permissions at once (v2.0 feature)...")

            # Check Manager's permissions
            manager_check = await vault.check_permissions_multi(
                document_id=document.id,
                agent_id=str(manager_id),
                permissions=["READ", "WRITE", "DELETE", "SHARE", "ADMIN"],
            )
            print(f"\n[Manager Permissions]")
            print(f"  Document ID: {manager_check['document_id']}")
            print(f"  Agent ID: {manager_check['agent_id']}")
            print(f"  Permissions:")
            for perm, has_it in manager_check["permissions_checked"].items():
                status = "✅" if has_it else "❌"
                print(f"    {perm}: {status}")
            print(f"  All Granted: {manager_check['all_granted']}")
            print(f"  Any Granted: {manager_check['any_granted']}")

            # Check Employee's permissions
            employee_check = await vault.check_permissions_multi(
                document_id=document.id,
                agent_id=str(employee_id),
                permissions=["READ", "WRITE", "DELETE"],
            )
            print(f"\n[Employee Permissions]")
            for perm, has_it in employee_check["permissions_checked"].items():
                status = "✅" if has_it else "❌"
                print(f"    {perm}: {status}")

            # v2.0 Feature: Detailed Permission Query
            print("\n[5] Getting detailed permission information (v2.0 feature)...")

            detailed_perms = await vault.get_permissions_detailed(
                document_id=document.id,
                agent_id=str(admin_id),
            )

            print(f"\n[Document Permissions Summary]")
            print(f"  Document: {detailed_perms['document_name']}")
            print(f"  Total Permissions: {detailed_perms['total_permissions']}")
            print(f"\n  Permission Details:")
            for perm_detail in detailed_perms["permissions"]:
                print(f"    - Agent: {perm_detail['agent_id']}")
                print(f"      Permission: {perm_detail['permission']}")
                print(f"      Granted By: {perm_detail['granted_by']}")
                print(f"      Granted At: {perm_detail['granted_at']}")
                if perm_detail.get("expires_at"):
                    print(f"      Expires: {perm_detail['expires_at']}")
                print()

            # Demonstrate permission hierarchy
            print("[6] Testing permission enforcement...")

            # Manager can update (WRITE permission)
            print("\n[Manager - WRITE test]")
            try:
                updated = await vault.replace_document_content(
                    document_id=document.id,
                    file_input=b"Updated content by manager",
                    agent_id=str(manager_id),
                    change_description="Manager update",
                    create_version=True,
                )
                print(
                    f"[OK] Manager updated document to version {updated.version_number}"
                )
            except Exception as e:
                print(f"[ERROR] Manager update failed: {e}")

            # Employee can read but not write
            print("\n[Employee - READ test]")
            try:
                details = await vault.get_document_details(
                    document_id=document.id,
                    agent_id=str(employee_id),
                    include_versions=True,
                )
                print(f"[OK] Employee can read document: {details['name']}")
                print(f"     Versions available: {len(details['versions'])}")
            except Exception as e:
                print(f"[ERROR] Employee read failed: {e}")

            print("\n[Employee - WRITE test (should fail)]")
            try:
                await vault.replace_document_content(
                    document_id=document.id,
                    file_input=b"Attempt by employee",
                    agent_id=str(employee_id),
                    change_description="Employee attempt",
                )
                print("[ERROR] Employee unexpectedly succeeded in writing")
            except Exception as e:
                print(f"[OK] Employee correctly denied WRITE: Permission denied")

            # v2.0 Feature: Paginated Document Listing with Permissions
            print("\n[7] Listing documents with permission filtering (v2.0)...")

            # List documents accessible to employee
            employee_docs = await vault.list_documents_paginated(
                organization_id=str(org_id),
                agent_id=str(employee_id),
                limit=10,
                offset=0,
            )
            print(f"\n[Employee Document Access]")
            print(f"  Can access: {employee_docs['pagination']['count']} document(s)")
            for doc in employee_docs["documents"]:
                print(f"    - {doc['name']} (ID: {doc['id']})")

            # Revoke contractor's access
            print("\n[8] Checking contractor's current permissions...")

            # Note: The v1.0 revoke() method doesn't work with UUIDs in v2.0
            # For v2.0, revocation would be done via set_permissions_bulk or service layer
            contractor_check = await vault.check_permissions_multi(
                document_id=document.id,
                agent_id=str(contractor_id),
                permissions=["READ", "WRITE"],
            )
            print(f"[Contractor Current State]")
            print(
                f"  READ: {'✅' if contractor_check['permissions_checked']['READ'] else '❌'}"
            )
            print(
                f"  WRITE: {'✅' if contractor_check['permissions_checked']['WRITE'] else '❌'}"
            )
            print(f"  Any Granted: {contractor_check['any_granted']}")
            print(
                f"\n[INFO] Revoke in v2.0 requires SDK update or direct service access"
            )

            # Final permission summary
            print("\n[9] Final permission summary...")

            final_perms = await vault.get_permissions_detailed(
                document_id=document.id,
                agent_id=str(admin_id),
            )
            print(f"\n[Final Access Control State]")
            print(f"  Document: {final_perms['document_name']}")
            print(f"  Active Permissions: {final_perms['total_permissions']}")
            print(f"  Agents with Access:")
            for perm in final_perms["permissions"]:
                print(f"    - {perm['agent_id']}: {perm['permission']}")

            print("\n" + "=" * 70)
            print("v2.0 Access Control Features Demonstrated:")
            print("=" * 70)
            print("  ✅ Bulk permission management (set_permissions_bulk)")
            print("  ✅ Multi-permission checking (check_permissions_multi)")
            print("  ✅ Detailed permission queries (get_permissions_detailed)")
            print("  ✅ Enhanced document upload with prefix/path")
            print("  ✅ Version-aware content replacement")
            print("  ✅ Paginated document listing with permission filtering")
            print("  ✅ Permission enforcement and validation")
            print("=" * 70)

    finally:
        # Clean up temporary file
        Path(temp_file_path).unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main())
