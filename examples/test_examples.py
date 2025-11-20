"""
Test runner for examples - validates v2.0 implementation.
"""

import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


async def test_basic_usage_v2():
    """Test the basic_usage_v2 example."""
    print("\n" + "=" * 70)
    print("Testing: basic_usage_v2.py")
    print("=" * 70)

    try:
        from uuid import uuid4
        from doc_vault import DocVaultSDK

        # Quick smoke test - just initialize
        async with DocVaultSDK() as vault:
            print("[OK] SDK initialized successfully")

            # Test organization registration
            org_id = uuid4()
            org = await vault.register_organization(
                external_id=str(org_id),
                name="Test Org",
                metadata={"test": True},
            )
            print(f"[OK] Organization registered: {org.id}")

            # Test agent registration
            agent_id = uuid4()
            agent = await vault.register_agent(
                external_id=str(agent_id),
                organization_id=str(org_id),
                name="Test Agent",
                email="test@example.com",
                agent_type="ai",
                metadata={"test": True},
            )
            print(f"[OK] Agent registered: {agent.id}")

            # Test enhanced upload with bytes
            sample_content = b"Test document content for v2.0"
            document = await vault.upload_enhanced(
                file_input=sample_content,
                name="test_doc.txt",
                organization_id=org_id,
                agent_id=agent_id,
                description="Test document",
                tags=["test"],
            )
            print(f"[OK] Document uploaded: {document.id}")

            # Test document details
            details = await vault.get_document_details(
                document_id=document.id,
                agent_id=agent_id,
                include_versions=True,
            )
            print(f"[OK] Document details retrieved: {details['name']}")

            # Test paginated listing
            result = await vault.list_documents_paginated(
                organization_id=org_id,
                agent_id=agent_id,
                limit=10,
                offset=0,
            )
            print(f"[OK] Document listing: {result['pagination']['count']} documents")

            # Test bulk permissions
            agent2_id = uuid4()
            agent2 = await vault.register_agent(
                external_id=str(agent2_id),
                organization_id=str(org_id),
                name="Test Agent 2",
                email="test2@example.com",
                agent_type="ai",
            )
            print(f"[OK] Second agent registered: {agent2.id}")

            permissions = [
                {"agent_id": agent2_id, "permission": "READ"},
            ]
            acls = await vault.set_permissions_bulk(
                document_id=document.id,
                permissions=permissions,
                granted_by=agent_id,
            )
            print(f"[OK] Permissions granted: {len(acls)} ACL(s)")

            # Test multi-permission check
            check_result = await vault.check_permissions_multi(
                document_id=document.id,
                agent_id=agent2_id,
                permissions=["READ", "WRITE"],
            )
            print(
                f"[OK] Permission check: READ={check_result['permissions_checked']['READ']}"
            )

            # Test content replacement
            new_content = b"Updated content"
            updated_doc = await vault.replace_document_content(
                document_id=document.id,
                file_input=new_content,
                agent_id=agent_id,
                create_version=True,
            )
            print(f"[OK] Content replaced: version {updated_doc.version_number}")

            print("\n" + "=" * 70)
            print("[SUCCESS] All v2.0 features tested successfully!")
            print("=" * 70)
            return True

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all example tests."""
    print("\n" + "=" * 70)
    print("DocVault v2.0 Example Test Suite")
    print("=" * 70)

    success = await test_basic_usage_v2()

    if success:
        print("\n[SUCCESS] All tests passed!")
        sys.exit(0)
    else:
        print("\n[FAILED] Some tests failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
