"""
Multi-organization example for DocVault SDK.

This example demonstrates multi-organization usage patterns:
- Managing multiple organizations
- Cross-organization document sharing
- Organization-specific access control
- Agent membership across organizations
"""

import asyncio
import tempfile
from pathlib import Path

from doc_vault import DocVaultSDK


async def main():
    """Main multi-organization example function."""
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
            print("🚀 DocVault SDK initialized for multi-organization demonstration!")

            # Create multiple organizations
            print("\n🏢 Creating multiple organizations...")

            tech_org = await vault.register_organization(
                external_id="tech-corp-001",
                name="TechCorp Solutions",
                metadata={
                    "industry": "technology",
                    "size": "enterprise",
                    "focus": "software_development",
                },
            )
            print(f"✅ Organization 1: {tech_org.name}")

            finance_org = await vault.register_organization(
                external_id="finance-group-001",
                name="Finance Group Inc",
                metadata={
                    "industry": "finance",
                    "size": "large",
                    "focus": "financial_services",
                },
            )
            print(f"✅ Organization 2: {finance_org.name}")

            consulting_org = await vault.register_organization(
                external_id="consulting-llc-001",
                name="Global Consulting LLC",
                metadata={
                    "industry": "consulting",
                    "size": "mid",
                    "focus": "business_consulting",
                },
            )
            print(f"✅ Organization 3: {consulting_org.name}")

            # Create agents in different organizations
            print("\n👥 Creating agents across organizations...")

            # TechCorp agents
            tech_lead = await vault.register_agent(
                external_id="tech-lead-001",
                organization_id="tech-corp-001",
                name="Sarah Johnson",
                email="sarah.johnson@techcorp.com",
                agent_type="human",
                metadata={"role": "engineering_lead", "department": "engineering"},
            )
            print(f"✅ TechCorp Lead: {tech_lead.name}")

            tech_dev = await vault.register_agent(
                external_id="tech-dev-001",
                organization_id="tech-corp-001",
                name="Mike Chen",
                email="mike.chen@techcorp.com",
                agent_type="human",
                metadata={"role": "developer", "department": "engineering"},
            )
            print(f"✅ TechCorp Developer: {tech_dev.name}")

            # Finance Group agents
            finance_director = await vault.register_agent(
                external_id="finance-dir-001",
                organization_id="finance-group-001",
                name="Emily Rodriguez",
                email="emily.rodriguez@finance.com",
                agent_type="human",
                metadata={"role": "director", "department": "finance"},
            )
            print(f"✅ Finance Director: {finance_director.name}")

            # Consulting agents
            consultant = await vault.register_agent(
                external_id="consultant-001",
                organization_id="consulting-llc-001",
                name="David Kim",
                email="david.kim@consulting.com",
                agent_type="human",
                metadata={"role": "senior_consultant", "department": "strategy"},
            )
            print(f"✅ Senior Consultant: {consultant.name}")

            # Upload documents in different organizations
            print("\n📤 Uploading documents to different organizations...")

            # TechCorp document
            tech_doc = await vault.upload(
                file_path=temp_files[0],
                name="System Architecture Design",
                organization_id="tech-corp-001",
                agent_id="tech-lead-001",
                description="Technical architecture document for new system",
                tags=["architecture", "technical", "design"],
                metadata={
                    "project": "enterprise_system",
                    "confidential": True,
                    "review_status": "pending",
                },
            )
            print(f"✅ TechCorp Document: {tech_doc.name}")

            # Finance document
            finance_doc = await vault.upload(
                file_path=temp_files[1],
                name="Financial Analysis Report",
                organization_id="finance-group-001",
                agent_id="finance-dir-001",
                description="Q4 financial analysis and projections",
                tags=["finance", "analysis", "quarterly"],
                metadata={
                    "quarter": "Q4_2024",
                    "confidential": True,
                    "reviewed_by": "audit_team",
                },
            )
            print(f"✅ Finance Document: {finance_doc.name}")

            # Demonstrate organization isolation
            print("\n🔒 Demonstrating organization isolation...")

            # TechCorp agents can only see TechCorp documents
            tech_docs = await vault.list_documents(
                organization_id="tech-corp-001", agent_id="tech-dev-001"
            )
            print(
                f"TechCorp Developer can see {len(tech_docs)} document(s) in TechCorp"
            )

            # Finance director can only see Finance documents
            finance_docs = await vault.list_documents(
                organization_id="finance-group-001", agent_id="finance-dir-001"
            )
            print(
                f"Finance Director can see {len(finance_docs)} document(s) in Finance Group"
            )

            # Consultant cannot see documents from other organizations
            consultant_tech_docs = await vault.list_documents(
                organization_id="tech-corp-001", agent_id="consultant-001"
            )
            print(
                f"Consultant can see {len(consultant_tech_docs)} document(s) in TechCorp (should be 0)"
            )

            # Demonstrate cross-organization sharing
            print("\n🤝 Demonstrating cross-organization sharing...")

            # TechCorp lead shares architecture document with consultant
            await vault.share(
                document_id=tech_doc.id,
                agent_id="consultant-001",
                permission="READ",
                granted_by="tech-lead-001",
            )
            print("✅ TechCorp shared architecture document with Consultant")

            # Finance director shares financial report with TechCorp lead
            await vault.share(
                document_id=finance_doc.id,
                agent_id="tech-lead-001",
                permission="READ",
                granted_by="finance-dir-001",
            )
            print("✅ Finance shared analysis report with TechCorp Lead")

            # Check what each agent can access now
            print("\n📋 Checking accessible documents after sharing...")

            # Consultant can now access the shared TechCorp document
            consultant_accessible = await vault.list_accessible_documents(
                agent_id="consultant-001",
                organization_id="consulting-llc-001",  # Note: using their own org for listing
            )
            print(f"Consultant can now access {len(consultant_accessible)} document(s)")

            # TechCorp lead can access both their own docs and the shared finance doc
            tech_lead_accessible = await vault.list_accessible_documents(
                agent_id="tech-lead-001", organization_id="tech-corp-001"
            )
            print(f"TechCorp Lead can access {len(tech_lead_accessible)} document(s)")

            # Verify consultant can read the shared document
            print("\n📖 Verifying consultant can read shared document...")

            try:
                shared_content = await vault.download(
                    document_id=tech_doc.id, agent_id="consultant-001"
                )
                print(
                    f"✅ Consultant successfully downloaded shared document: {len(shared_content)} bytes"
                )
            except Exception as e:
                print(f"❌ Consultant failed to access shared document: {e}")

            # TechCorp lead can read the shared finance document
            try:
                finance_content = await vault.download(
                    document_id=finance_doc.id, agent_id="tech-lead-001"
                )
                print(
                    f"✅ TechCorp Lead successfully downloaded shared finance document: {len(finance_content)} bytes"
                )
            except Exception as e:
                print(f"❌ TechCorp Lead failed to access shared finance document: {e}")

            # Demonstrate permission levels in sharing
            print("\n🔐 Demonstrating permission levels in cross-org sharing...")

            # TechCorp developer gets WRITE permission on the architecture document
            await vault.share(
                document_id=tech_doc.id,
                agent_id="tech-dev-001",
                permission="WRITE",
                granted_by="tech-lead-001",
            )
            print(
                "✅ TechCorp Lead shared architecture document with Developer (WRITE permission)"
            )

            # Consultant only gets READ permission
            consultant_can_write = await vault.check_permission(
                document_id=tech_doc.id, agent_id="consultant-001", permission="WRITE"
            )
            print(
                f"Consultant has WRITE permission: {'✅' if consultant_can_write else '❌'}"
            )

            dev_can_write = await vault.check_permission(
                document_id=tech_doc.id, agent_id="tech-dev-001", permission="WRITE"
            )
            print(
                f"TechCorp Developer has WRITE permission: {'✅' if dev_can_write else '❌'}"
            )

            # Demonstrate revoking cross-organization access
            print("\n🚫 Demonstrating access revocation...")

            # TechCorp lead revokes consultant's access
            await vault.revoke_access(
                document_id=tech_doc.id,
                agent_id="consultant-001",
                revoked_by="tech-lead-001",
            )
            print("✅ TechCorp Lead revoked Consultant's access")

            # Verify consultant can no longer access
            try:
                await vault.download(document_id=tech_doc.id, agent_id="consultant-001")
                print("❌ Consultant unexpectedly can still access revoked document")
            except Exception as e:
                print(f"✅ Consultant correctly denied access to revoked document: {e}")

            # Show final access summary
            print("\n📊 Final access summary...")

            # Get all organizations
            all_orgs = []  # In a real scenario, you'd have a list_orgs method
            org_ids = ["tech-corp-001", "finance-group-001", "consulting-llc-001"]

            for org_id in org_ids:
                # Count documents in each org
                if org_id == "tech-corp-001":
                    agent_id = "tech-lead-001"
                elif org_id == "finance-group-001":
                    agent_id = "finance-dir-001"
                else:
                    agent_id = "consultant-001"

                docs = await vault.list_documents(
                    organization_id=org_id, agent_id=agent_id
                )
                print(f"Organization {org_id}: {len(docs)} document(s)")

            print("\n🎉 Multi-organization demonstration completed!")
            print("\nKey concepts demonstrated:")
            print("  ✅ Multiple organization management")
            print("  ✅ Organization-level data isolation")
            print("  ✅ Cross-organization document sharing")
            print("  ✅ Permission levels in sharing")
            print("  ✅ Access revocation")
            print("  ✅ Agent membership and access control")

    finally:
        # Clean up temporary files
        for temp_file in temp_files:
            Path(temp_file).unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main())
