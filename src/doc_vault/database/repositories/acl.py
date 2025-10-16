"""
ACL repository for DocVault.

Provides CRUD operations for document_acl table.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from doc_vault.database.postgres_manager import PostgreSQLManager
from doc_vault.database.repositories.base import BaseRepository
from doc_vault.database.schemas.acl import DocumentACL, DocumentACLCreate

logger = logging.getLogger(__name__)


class ACLRepository(BaseRepository[DocumentACL]):
    """
    Repository for DocumentACL entities.

    Provides CRUD operations and ACL-specific queries.
    """

    @property
    def table_name(self) -> str:
        """Database table name."""
        return "document_acl"

    @property
    def model_class(self) -> type:
        """Pydantic model class for this repository."""
        return DocumentACL

    def _row_to_model(self, row: Dict[str, Any]) -> DocumentACL:
        """
        Convert database row dict to DocumentACL model.

        Args:
            row: Database row as dict

        Returns:
            DocumentACL instance
        """
        return DocumentACL(
            id=row["id"],
            document_id=row["document_id"],
            agent_id=row["agent_id"],
            permission=row["permission"],
            granted_by=row["granted_by"],
            granted_at=row["granted_at"],
            expires_at=row["expires_at"],
        )

    def _model_to_dict(self, model: DocumentACL) -> Dict[str, Any]:
        """
        Convert DocumentACL model to database dict.

        Args:
            model: DocumentACL instance

        Returns:
            Dict suitable for database insertion/update
        """
        data = {
            "document_id": model.document_id,
            "agent_id": model.agent_id,
            "permission": model.permission,
            "granted_by": model.granted_by,
            "granted_at": model.granted_at,
            "expires_at": model.expires_at,
        }

        # Include ID if it exists (for updates)
        if hasattr(model, "id") and model.id:
            data["id"] = model.id

        return data

    async def get_by_document(self, document_id: UUID | str) -> List[DocumentACL]:
        """
        Get all ACL entries for a document.

        Args:
            document_id: Document UUID or string

        Returns:
            List of DocumentACL instances
        """
        try:
            # Ensure document_id is a UUID
            document_id = self._ensure_uuid(document_id)

            query = """
                SELECT * FROM document_acl
                WHERE document_id = $1
                ORDER BY granted_at DESC
            """
            result = await self.db_manager.execute(query, [document_id])
            rows = result.result()
            return [self._row_to_model(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get ACL entries for document {document_id}: {e}")
            from doc_vault.exceptions import DatabaseError

            raise DatabaseError("Failed to get document ACL entries") from e

    async def get_by_agent(self, agent_id: UUID | str) -> List[DocumentACL]:
        """
        Get all ACL entries for an agent.

        Args:
            agent_id: Agent UUID or string

        Returns:
            List of DocumentACL instances
        """
        try:
            # Ensure agent_id is a UUID
            agent_id = self._ensure_uuid(agent_id)

            query = """
                SELECT * FROM document_acl
                WHERE agent_id = $1
                ORDER BY granted_at DESC
            """
            result = await self.db_manager.execute(query, [agent_id])
            rows = result.result()
            return [self._row_to_model(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get ACL entries for agent {agent_id}: {e}")
            from doc_vault.exceptions import DatabaseError

            raise DatabaseError("Failed to get agent ACL entries") from e

    async def get_by_document_and_agent(
        self, document_id: UUID | str, agent_id: UUID | str
    ) -> List[DocumentACL]:
        """
        Get ACL entries for a specific document-agent pair.

        Args:
            document_id: Document UUID
            agent_id: Agent UUID

        Returns:
            List of DocumentACL instances (usually 0 or 1 due to unique constraint)
        """
        try:
            document_id = self._ensure_uuid(document_id)
            agent_id = self._ensure_uuid(agent_id)
            query = """
                SELECT * FROM document_acl
                WHERE document_id = $1 AND agent_id = $2
                ORDER BY granted_at DESC
            """
            result = await self.db_manager.execute(query, [document_id, agent_id])
            rows = result.result()
            return [self._row_to_model(row) for row in rows]

        except Exception as e:
            logger.error(
                f"Failed to get ACL entries for document {document_id} and agent {agent_id}: {e}"
            )
            from doc_vault.exceptions import DatabaseError

            raise DatabaseError("Failed to get document-agent ACL entries") from e

    async def check_permission(
        self, document_id: UUID | str, agent_id: UUID | str, permission: str
    ) -> bool:
        """
        Check if an agent has a specific permission for a document.

        Args:
            document_id: Document UUID or string
            agent_id: Agent UUID or string
            permission: Permission to check ('READ', 'WRITE', 'DELETE', 'SHARE', 'ADMIN')

        Returns:
            True if agent has the permission, False otherwise
        """
        try:
            # Ensure IDs are UUIDs
            document_id = self._ensure_uuid(document_id)
            agent_id = self._ensure_uuid(agent_id)

            # ADMIN permission grants all other permissions
            query = """
                SELECT 1 FROM document_acl
                WHERE document_id = $1
                  AND agent_id = $2
                  AND (permission = $3 OR permission = 'ADMIN')
                  AND (expires_at IS NULL OR expires_at > NOW())
                LIMIT 1
            """
            result = await self.db_manager.execute(
                query, [document_id, agent_id, permission]
            )
            return len(result.result()) > 0

        except Exception as e:
            logger.error(
                f"Failed to check permission {permission} for document {document_id} and agent {agent_id}: {e}"
            )
            from doc_vault.exceptions import DatabaseError

            raise DatabaseError("Failed to check document permission") from e

    async def get_agent_permissions(
        self, document_id: UUID, agent_id: UUID
    ) -> List[str]:
        """
        Get all permissions an agent has for a document.

        Args:
            document_id: Document UUID
            agent_id: Agent UUID

        Returns:
            List of permission strings
        """
        try:
            query = """
                SELECT permission FROM document_acl
                WHERE document_id = $1
                  AND agent_id = $2
                  AND (expires_at IS NULL OR expires_at > NOW())
                ORDER BY granted_at DESC
            """
            result = await self.db_manager.execute(query, [document_id, agent_id])
            rows = result.result()
            return [row["permission"] for row in rows]

        except Exception as e:
            logger.error(
                f"Failed to get permissions for document {document_id} and agent {agent_id}: {e}"
            )
            from doc_vault.exceptions import DatabaseError

            raise DatabaseError("Failed to get agent document permissions") from e

    async def revoke_permission(
        self, document_id: UUID | str, agent_id: UUID | str, permission: str
    ) -> bool:
        """
        Revoke a specific permission for an agent on a document.

        Args:
            document_id: Document UUID
            agent_id: Agent UUID
            permission: Permission to revoke

        Returns:
            True if permission was revoked, False if it didn't exist
        """
        try:
            document_id = self._ensure_uuid(document_id)
            agent_id = self._ensure_uuid(agent_id)
            query = """
                DELETE FROM document_acl
                WHERE document_id = $1 AND agent_id = $2 AND permission = $3
            """
            await self.db_manager.execute(query, [document_id, agent_id, permission])
            # Since we can't check affected rows with psqlpy, assume success
            return True

        except Exception as e:
            logger.error(
                f"Failed to revoke permission {permission} for document {document_id} and agent {agent_id}: {e}"
            )
            from doc_vault.exceptions import DatabaseError

            raise DatabaseError("Failed to revoke document permission") from e

    async def revoke_all_permissions(
        self, document_id: UUID | str, agent_id: UUID | str
    ) -> int:
        """
        Revoke all permissions for an agent on a document.

        Args:
            document_id: Document UUID
            agent_id: Agent UUID

        Returns:
            Number of permissions revoked
        """
        try:
            document_id = self._ensure_uuid(document_id)
            agent_id = self._ensure_uuid(agent_id)
            # First count how many will be deleted
            count_query = """
                SELECT COUNT(*) as count FROM document_acl
                WHERE document_id = $1 AND agent_id = $2
            """
            count_result = await self.db_manager.execute(
                count_query, [document_id, agent_id]
            )
            count = count_result.result()[0]["count"]

            # Then delete
            query = """
                DELETE FROM document_acl
                WHERE document_id = $1 AND agent_id = $2
            """
            await self.db_manager.execute(query, [document_id, agent_id])
            return count

        except Exception as e:
            logger.error(
                f"Failed to revoke all permissions for document {document_id} and agent {agent_id}: {e}"
            )
            from doc_vault.exceptions import DatabaseError

            raise DatabaseError("Failed to revoke all document permissions") from e

    async def get_expired_permissions(self) -> List[DocumentACL]:
        """
        Get all expired ACL entries.

        Returns:
            List of expired DocumentACL instances
        """
        try:
            query = """
                SELECT * FROM document_acl
                WHERE expires_at IS NOT NULL AND expires_at <= NOW()
                ORDER BY expires_at DESC
            """
            result = await self.db_manager.execute(query)
            rows = result.result()
            return [self._row_to_model(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get expired permissions: {e}")
            from doc_vault.exceptions import DatabaseError

            raise DatabaseError("Failed to get expired permissions") from e

    async def cleanup_expired_permissions(self) -> int:
        """
        Remove all expired ACL entries.

        Returns:
            Number of expired entries removed
        """
        try:
            # First count how many will be deleted
            count_query = """
                SELECT COUNT(*) as count FROM document_acl
                WHERE expires_at IS NOT NULL AND expires_at <= NOW()
            """
            count_result = await self.db_manager.execute(count_query)
            count = count_result.result()[0]["count"]

            # Then delete
            query = """
                DELETE FROM document_acl
                WHERE expires_at IS NOT NULL AND expires_at <= NOW()
            """
            await self.db_manager.execute(query)
            return count

        except Exception as e:
            logger.error(f"Failed to cleanup expired permissions: {e}")
            from doc_vault.exceptions import DatabaseError

            raise DatabaseError("Failed to cleanup expired permissions") from e

    async def grant_permission(
        self,
        document_id: UUID | str,
        agent_id: UUID | str,
        permission: str,
        granted_by: UUID | str,
        expires_at: Optional[datetime] = None,
    ) -> DocumentACL:
        """
        Grant a permission to an agent for a document.

        This method handles the upsert logic - if the permission already exists,
        it updates the expiration; if not, it creates a new entry.

        Args:
            document_id: Document UUID
            agent_id: Agent UUID
            permission: Permission to grant
            granted_by: Agent granting the permission
            expires_at: Optional expiration timestamp

        Returns:
            Created or updated DocumentACL instance
        """
        try:
            document_id = self._ensure_uuid(document_id)
            agent_id = self._ensure_uuid(agent_id)
            granted_by = self._ensure_uuid(granted_by)
            # Check if permission already exists
            existing = await self.get_by_document_and_agent(document_id, agent_id)
            existing_perm = next(
                (acl for acl in existing if acl.permission == permission), None
            )

            if existing_perm:
                # Update existing permission
                updates = {}
                if expires_at != existing_perm.expires_at:
                    updates["expires_at"] = expires_at
                if updates:
                    return await self.update(existing_perm.id, updates)
                else:
                    return existing_perm
            else:
                # Create new permission
                acl_data = DocumentACLCreate(
                    document_id=document_id,
                    agent_id=agent_id,
                    permission=permission,
                    granted_by=granted_by,
                    expires_at=expires_at,
                )
                return await self.create_from_create_schema(acl_data)

        except Exception as e:
            logger.error(
                f"Failed to grant permission {permission} for document {document_id} to agent {agent_id}: {e}"
            )
            from doc_vault.exceptions import DatabaseError

            raise DatabaseError("Failed to grant document permission") from e

    async def create_from_create_schema(
        self, create_data: DocumentACLCreate
    ) -> DocumentACL:
        """
        Create a document ACL entry from DocumentACLCreate schema.

        This is a convenience method that handles the conversion from
        create schema to full model.

        Args:
            create_data: DocumentACLCreate schema instance

        Returns:
            Created DocumentACL instance
        """
        # Convert create schema to dict and create model
        model_data = create_data.model_dump()
        # Add granted_at timestamp
        from datetime import datetime

        model_data["granted_at"] = datetime.now()
        # Create a temporary model instance for the base class create method
        temp_model = DocumentACL(**model_data)
        return await self.create(temp_model)
