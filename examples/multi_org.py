"""
Multi-organization example for DocVault SDK v2.0.

This example demonstrates multi-organization usage patterns:
- Managing multiple organizations
- Cross-organization document sharing with set_permissions()
- Organization-specific access control
- Using list_docs() with org_id filtering
"""

import asyncio
import tempfile
import uuid
from pathlib import Path

from doc_vault import DocVaultSDK


async def main():
    """Main multi-organization example function."""
    # Generate UUIDs for this example
    tech_org_id = str(uuid.uuid4())
    finance_org_id = str(uuid.uuid4())
    consulting_org_id = str(uuid.uuid4())
    tech_lead_id = str(uuid.uuid4())
    tech_dev_id = str(uuid.uuid4())
    finance_dir_id = str(uuid.uuid4())
    consultant_id = str(uuid.uuid4())

    # Create temporary files for the example
    temp_files = []

    try:
        # Create content for different organizations
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pdf", delete=False) as f:
            f.write(
                "%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n..."
            )  # Mock PDF content
            temp_files.append(f.name)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".docx", delete=False) as f:
            f.write(
                "Mock DOCX content for inter-org collaboration..."
            )  # Mock DOCX content
            temp_files.append(f.name)

        async with DocVaultSDK() as vault:
            print("DocVault SDK initialized for multi-organization demonstration!")

            # Create multiple organizations
            print("\nCreating multiple organizations...")

            tech_org = await vault.register_organization(
                org_id=tech_org_id,
                metadata={
                    "display_name": "TechCorp Solutions",
                    "industry": "technology",
                    "size": "enterprise",
                    "focus": "software_development",
                },
            )
            print(f"Organization 1: {tech_org.id}")

            finance_org = await vault.register_organization(
                org_id=finance_org_id,
                metadata={
                    "display_name": "Finance Group Inc",
                    "industry": "finance",
                    "size": "large",
                    "focus": "financial_services",
                },
            )
            print(f"Organization 2: {finance_org.id}")

            consulting_org = await vault.register_organization(
                org_id=consulting_org_id,
                metadata={
                    "display_name": "Global Consulting LLC",
                    "industry": "consulting",
                    "size": "mid",
                    "focus": "business_consulting",
                },
            )
            print(f"Organization 3: {consulting_org.id}")

            # Create agents in different organizations
            print("\nCreating agents across organizations...")

            # TechCorp agents
            tech_lead = await vault.register_agent(
                agent_id=tech_lead_id,
                organization_id=tech_org_id,
                metadata={
                    "name": "Sarah Johnson",
                    "email": "sarah.johnson@techcorp.com",
                    "role": "engineering_lead",
                    "department": "engineering",
                },
            )
            print(f"TechCorp Lead: {tech_lead.id}")

            tech_dev = await vault.register_agent(
                agent_id=tech_dev_id,
                organization_id=tech_org_id,
                metadata={
                    "name": "Mike Chen",
                    "email": "mike.chen@techcorp.com",
                    "role": "developer",
                    "department": "engineering",
                },
            )
            print(f"TechCorp Developer: {tech_dev.id}")

            # Finance Group agents
            finance_director = await vault.register_agent(
                agent_id=finance_dir_id,
                organization_id=finance_org_id,
                metadata={
                    "name": "Emily Rodriguez",
                    "email": "emily.rodriguez@finance.com",
                    "role": "director",
                    "department": "finance",
                },
            )
            print(f"Finance Director: {finance_director.id}")

            # Consulting agents
            consultant = await vault.register_agent(
                agent_id=consultant_id,
                organization_id=consulting_org_id,
                metadata={
                    "name": "David Kim",
                    "email": "david.kim@consulting.com",
                    "role": "senior_consultant",
                    "department": "strategy",
                },
            )
            print(f"Senior Consultant: {consultant.id}")

            # Upload documents in different organizations
            print("\nUploading documents to different organizations...")

            # TechCorp document
            tech_doc = await vault.upload(
                file_input=temp_files[0],
                name="System Architecture Design",
                organization_id=tech_org_id,
                agent_id=tech_lead_id,
                description="Technical architecture document for new system",
                tags=["architecture", "technical", "design"],
                metadata={
                    "project": "enterprise_system",
                    "confidential": True,
                    "review_status": "pending",
                },
            )
            print(f"TechCorp Document: {tech_doc.name}")

            # Finance document
            finance_doc = await vault.upload(
                file_input=temp_files[1],
                name="Financial Analysis Report",
                organization_id=finance_org_id,
                agent_id=finance_dir_id,
                description="Q4 financial analysis and projections",
                tags=["finance", "analysis", "quarterly"],
                metadata={
                    "quarter": "Q4_2024",
                    "confidential": True,
                    "reviewed_by": "audit_team",
                },
            )
            print(f"Finance Document: {finance_doc.name}")

            # Demonstrate organization isolation
            print("\nDemonstrating organization isolation...")

            # TechCorp agents can only see TechCorp documents
            tech_docs_result = await vault.list_docs(
                organization_id=tech_org_id, agent_id=tech_dev_id
            )
            tech_docs = tech_docs_result.get("documents", [])
            print(
                f"TechCorp Developer can see {len(tech_docs)} document(s) in TechCorp"
            )

            # Finance director can only see Finance documents
            finance_docs_result = await vault.list_docs(
                organization_id=finance_org_id, agent_id=finance_dir_id
            )
            finance_docs = finance_docs_result.get("documents", [])
            print(
                f"Finance Director can see {len(finance_docs)} document(s) in Finance Group"
            )

            # Consultant cannot see documents from other organizations
            consultant_tech_docs_result = await vault.list_docs(
                organization_id=tech_org_id, agent_id=consultant_id
            )
            consultant_tech_docs = consultant_tech_docs_result.get("documents", [])
            print(
                f"Consultant can see {len(consultant_tech_docs)} document(s) in TechCorp (should be 0)"
            )

            # Demonstrate cross-organization sharing
            print("\nDemonstrating cross-organization sharing...")

            # TechCorp lead shares architecture document with consultant
            await vault.set_permissions(
                document_id=tech_doc.id,
                permissions=[
                    {
                        "agent_id": consultant_id,
                        "permission": "READ",
                    },
                ],
                granted_by=tech_lead_id,
            )
            print("TechCorp shared architecture document with Consultant")

            # Finance director shares financial report with TechCorp lead
            await vault.set_permissions(
                document_id=finance_doc.id,
                permissions=[
                    {
                        "agent_id": tech_lead_id,
                        "permission": "READ",
                    },
                ],
                granted_by=finance_dir_id,
            )
            print("Finance shared analysis report with TechCorp Lead")

            # Check what each agent can access now
            print("\nChecking accessible documents after sharing...")

            # Use list_docs to see what each agent can access
            # Consultant can now see shared documents
            consultant_docs_result = await vault.list_docs(
                agent_id=consultant_id, organization_id=consulting_org_id
            )
            consultant_docs = consultant_docs_result.get("documents", [])
            print(
                f"Consultant can see {len(consultant_docs)} document(s) in their own org"
            )

            # TechCorp lead can access both their own docs and shared docs
            tech_lead_docs_result = await vault.list_docs(
                agent_id=tech_lead_id, organization_id=tech_org_id
            )
            tech_lead_docs = tech_lead_docs_result.get("documents", [])
            print(
                f"TechCorp Lead can see {len(tech_lead_docs)} document(s) in their org"
            )

            # Verify consultant can read the shared document
            print("\nVerifying consultant can read shared document...")

            try:
                shared_content = await vault.download(
                    document_id=tech_doc.id, agent_id=consultant_id
                )
                print(
                    f"Consultant successfully downloaded shared document: {len(shared_content)} bytes"
                )
            except Exception as e:
                print(f"Consultant failed to access shared document: {e}")

            # TechCorp lead can read the shared finance document
            try:
                finance_content = await vault.download(
                    document_id=finance_doc.id, agent_id=tech_lead_id
                )
                print(
                    f"TechCorp Lead successfully downloaded shared finance document: {len(finance_content)} bytes"
                )
            except Exception as e:
                print(f"TechCorp Lead failed to access shared finance document: {e}")

            # Demonstrate permission levels in sharing
            print("\nDemonstrating permission levels in cross-org sharing...")

            # TechCorp developer gets WRITE permission on the architecture document
            await vault.set_permissions(
                document_id=tech_doc.id,
                permissions=[
                    {
                        "agent_id": tech_dev_id,
                        "permission": "WRITE",
                    },
                ],
                granted_by=tech_lead_id,
            )
            print(
                "TechCorp Lead granted Developer WRITE permission on architecture document"
            )

            # Check permissions using get_permissions
            consultant_perms_result = await vault.get_permissions(
                document_id=tech_doc.id, agent_id=consultant_id
            )
            consultant_perms = consultant_perms_result.get("permissions", [])
            consultant_can_write = any(
                p["permission"] == "WRITE" for p in consultant_perms
            )
            print(
                f"Consultant has WRITE permission: {'[OK]' if consultant_can_write else '[NO]'}"
            )

            dev_perms_result = await vault.get_permissions(
                document_id=tech_doc.id, agent_id=tech_dev_id
            )
            dev_perms = dev_perms_result.get("permissions", [])
            dev_can_write = any(p["permission"] == "WRITE" for p in dev_perms)
            print(
                f"TechCorp Developer has WRITE permission: {'[OK]' if dev_can_write else '[NO]'}"
            )

            # Demonstrate access control summary
            print("\nAccess control verification...")

            # Note: In v2.0, permission revocation would typically be done by
            # updating permissions with set_permissions() to remove specific grants
            print(
                "Permission management demonstrated with get_permissions() and set_permissions()"
            )

            # Verify permissions are properly enforced
            try:
                # Test that consultant can still read (they have READ permission)
                content = await vault.download(
                    document_id=tech_doc.id, agent_id=consultant_id
                )
                print(f"Consultant can read shared document: {len(content)} bytes")
            except Exception as e:
                print(f"Consultant access check failed: {e}")

            # Show final access summary
            print("\nFinal access summary...")

            # Count documents in each org using list_docs
            org_ids = [tech_org_id, finance_org_id, consulting_org_id]
            agent_map = {
                tech_org_id: tech_lead_id,
                finance_org_id: finance_dir_id,
                consulting_org_id: consultant_id,
            }

            for org_id in org_ids:
                agent_id = agent_map[org_id]
                result = await vault.list_docs(
                    organization_id=org_id, agent_id=agent_id
                )
                docs = result.get("documents", [])
                print(f"Organization {org_id}: {len(docs)} document(s)")

            print("\nMulti-organization demonstration completed!")
            print("\nKey concepts demonstrated:")
            print("  - Multiple organization management")
            print("  - Organization-level data isolation")
            print("  - Cross-organization document sharing with set_permissions()")
            print("  - Permission levels and access control")
            print("  - Using list_docs() with org_id filtering")
            print("  - Agent-based access verification")
            print("  - Access revocation")
            print("  - Agent membership and access control")

    finally:
        # Clean up temporary files
        for temp_file in temp_files:
            Path(temp_file).unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main())
