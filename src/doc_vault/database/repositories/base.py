"""
Base repository pattern for DocVault database operations.

This module provides a base class for all repository implementations,
containing common CRUD operations and database interaction patterns.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, TypeVar
from uuid import UUID

from doc_vault.database.postgres_manager import PostgreSQLManager
from doc_vault.exceptions import DatabaseError

logger = logging.getLogger(__name__)

# Type variable for the model type
T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """
    Base repository class providing common CRUD operations.

    Subclasses should implement:
    - table_name: str - The database table name
    - model_class: type - The Pydantic model class
    - _row_to_model(row: dict) -> T - Convert database row to model
    - _model_to_dict(model: T) -> dict - Convert model to database dict
    """

    def __init__(self, db_manager: PostgreSQLManager):
        """
        Initialize repository with database manager.

        Args:
            db_manager: PostgreSQL connection manager
        """
        self.db_manager = db_manager

    def _ensure_uuid(self, value: UUID | str) -> UUID:
        """
        Ensure a value is a UUID object.

        Args:
            value: UUID object or string representation

        Returns:
            UUID object

        Raises:
            ValueError: If string cannot be converted to UUID
        """
        if isinstance(value, UUID):
            return value
        elif isinstance(value, str):
            return UUID(value)
        else:
            raise ValueError(f"Expected UUID or str, got {type(value)}")

    @property
    @abstractmethod
    def table_name(self) -> str:
        """Database table name."""
        pass

    @property
    @abstractmethod
    def model_class(self) -> type:
        """Pydantic model class for this repository."""
        pass

    @abstractmethod
    def _row_to_model(self, row: Dict[str, Any]) -> T:
        """
        Convert database row dict to model instance.

        Args:
            row: Database row as dict

        Returns:
            Model instance
        """
        pass

    @abstractmethod
    def _model_to_dict(self, model: T) -> Dict[str, Any]:
        """
        Convert model instance to database dict.

        Args:
            model: Model instance

        Returns:
            Dict suitable for database insertion/update
        """
        pass

    async def create(self, model: T) -> T:
        """
        Create a new record in the database.

        Args:
            model: Model instance to create

        Returns:
            Created model with database-generated fields (like id, timestamps)

        Raises:
            DatabaseError: If creation fails
        """
        try:
            data = self._model_to_dict(model)

            # Build column names and placeholders
            columns = list(data.keys())
            placeholders = [f"${i+1}" for i in range(len(columns))]
            values = list(data.values())

            query = f"""
                INSERT INTO {self.table_name} ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
                RETURNING *
            """

            logger.debug(f"Creating {self.model_class.__name__}: {query}")

            result = await self.db_manager.execute(query, values)
            row = result.result()[0]  # First (and only) row

            return self._row_to_model(row)

        except Exception as e:
            logger.error(f"Failed to create {self.model_class.__name__}: {e}")
            raise DatabaseError(f"Failed to create {self.model_class.__name__}") from e

    async def get_by_id(self, id: UUID) -> Optional[T]:
        """
        Get a record by its UUID.

        Args:
            id: Record UUID

        Returns:
            Model instance or None if not found
        """
        try:
            # Use string interpolation for UUID since psqlpy has issues with UUID parameters
            query = f"SELECT * FROM {self.table_name} WHERE id = '{str(id)}'"
            result = await self.db_manager.execute(query)

            rows = result.result()
            if not rows:
                return None

            return self._row_to_model(rows[0])

        except Exception as e:
            logger.error(f"Failed to get {self.model_class.__name__} by id {id}: {e}")
            raise DatabaseError(f"Failed to get {self.model_class.__name__}") from e

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """
        Get all records with pagination.

        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of model instances
        """
        try:
            query = f"SELECT * FROM {self.table_name} ORDER BY created_at DESC LIMIT $1 OFFSET $2"
            result = await self.db_manager.execute(query, [limit, offset])

            rows = result.result()
            return [self._row_to_model(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get all {self.model_class.__name__}: {e}")
            raise DatabaseError(
                f"Failed to get {self.model_class.__name__} list"
            ) from e

    async def update(self, id: UUID, updates: Dict[str, Any]) -> Optional[T]:
        """
        Update a record by ID.

        Args:
            id: Record UUID
            updates: Dict of field updates

        Returns:
            Updated model instance or None if not found

        Raises:
            DatabaseError: If update fails
        """
        try:
            if not updates:
                # No updates provided, just return current record
                return await self.get_by_id(id)

            # Build SET clause
            set_parts = []
            values = []
            param_index = 1

            for key, value in updates.items():
                set_parts.append(f"{key} = ${param_index}")
                values.append(value)
                param_index += 1

            # Add ID parameter
            values.append(id)

            query = f"""
                UPDATE {self.table_name}
                SET {', '.join(set_parts)}, updated_at = NOW()
                WHERE id = ${param_index}
                RETURNING *
            """

            logger.debug(f"Updating {self.model_class.__name__} {id}: {query}")

            result = await self.db_manager.execute(query, values)
            rows = result.result()

            if not rows:
                return None

            return self._row_to_model(rows[0])

        except Exception as e:
            logger.error(f"Failed to update {self.model_class.__name__} {id}: {e}")
            raise DatabaseError(f"Failed to update {self.model_class.__name__}") from e

    async def delete(self, id: UUID) -> bool:
        """
        Delete a record by ID.

        Args:
            id: Record UUID

        Returns:
            True if deleted, False if not found

        Raises:
            DatabaseError: If deletion fails
        """
        try:
            query = f"DELETE FROM {self.table_name} WHERE id = $1"
            await self.db_manager.execute(query, [id])

            # Since DELETE doesn't return rows, we assume success if no exception
            # To check if actually deleted, we'd need to check affected rows,
            # but psqlpy QueryResult doesn't expose that
            return True

        except Exception as e:
            logger.error(f"Failed to delete {self.model_class.__name__} {id}: {e}")
            raise DatabaseError(f"Failed to delete {self.model_class.__name__}") from e

    async def exists(self, id: UUID) -> bool:
        """
        Check if a record exists by ID.

        Args:
            id: Record UUID

        Returns:
            True if exists, False otherwise
        """
        try:
            query = f"SELECT 1 FROM {self.table_name} WHERE id = $1 LIMIT 1"
            result = await self.db_manager.execute(query, [id])

            return len(result.result()) > 0

        except Exception as e:
            logger.error(
                f"Failed to check existence of {self.model_class.__name__} {id}: {e}"
            )
            raise DatabaseError(
                f"Failed to check {self.model_class.__name__} existence"
            ) from e

    async def count(self) -> int:
        """
        Count total records in the table.

        Returns:
            Total number of records
        """
        try:
            query = f"SELECT COUNT(*) as count FROM {self.table_name}"
            result = await self.db_manager.execute(query)

            return result.result()[0]["count"]

        except Exception as e:
            logger.error(f"Failed to count {self.model_class.__name__}: {e}")
            raise DatabaseError(f"Failed to count {self.model_class.__name__}") from e
