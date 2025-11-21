"""
PostgreSQL connection manager for DocVault SDK.

This module provides a connection pool manager using PSQLPy for high-performance
async PostgreSQL operations.
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from psqlpy import Connection, ConnectionPool

from doc_vault.config import Config

logger = logging.getLogger(__name__)


class PostgreSQLManager:
    """
    PostgreSQL connection manager using PSQLPy.

    Manages connection pool lifecycle and provides connections
    for repository operations.
    """

    def __init__(self, config: Config):
        """
        Initialize the manager (does NOT create pool yet).

        Args:
            config: Configuration object with database settings
        """
        self.config = config
        self._pool: Optional[ConnectionPool] = None
        self._initialized = False

        # Build PostgreSQL DSN (Data Source Name)
        # PSQLPy uses a different format than standard libpq
        self.dsn = (
            f"postgresql://{config.postgres_user}:{config.postgres_password}"
            f"@{config.postgres_host}:{config.postgres_port}/{config.postgres_db}"
        )

        # Add SSL mode if not disabled
        if config.postgres_ssl != "disable":
            self.dsn += f"?sslmode={config.postgres_ssl}"

        logger.info(
            f"PostgreSQL manager configured for "
            f"{config.postgres_host}:{config.postgres_port}/{config.postgres_db} "
            f"(SSL: {config.postgres_ssl})"
        )

    async def initialize(self) -> None:
        """
        Initialize the connection pool.

        Call this once during application startup.
        """
        if self._initialized:
            logger.warning("PostgreSQL manager already initialized")
            return

        if self._pool is None:
            # Create the connection pool with SSL context if needed
            pool_kwargs = {
                "dsn": self.dsn,
                "max_db_pool_size": 10,  # Default pool size
            }

            # Add SSL context if SSL is enabled
            if self.config.postgres_ssl_context is not None:
                pool_kwargs["ssl_context"] = self.config.postgres_ssl_context

            self._pool = ConnectionPool(**pool_kwargs)
            self._initialized = True
            logger.info("PostgreSQL connection pool initialized")

    async def close(self) -> None:
        """
        Close the connection pool and clean up resources.

        Call this during application shutdown.
        """
        if self._pool:
            self._pool.close()
            self._pool = None
            self._initialized = False
            logger.info("PostgreSQL connection pool closed")

    @asynccontextmanager
    async def connection(self):
        """
        Get a connection from the pool using context manager (RECOMMENDED).

        The connection is automatically returned to the pool when exiting the context.

        Usage:
            async with manager.connection() as conn:
                result = await conn.execute("SELECT * FROM users WHERE id = $1", [user_id])

        Yields:
            Connection: A database connection from the pool

        Raises:
            RuntimeError: If pool is not initialized
        """
        if not self._initialized or not self._pool:
            raise RuntimeError(
                "PostgreSQL manager not initialized. Call initialize() first."
            )

        # Get connection from pool
        conn: Connection = await self._pool.connection()
        try:
            yield conn
        finally:
            # Connection is automatically returned to pool
            # No explicit cleanup needed with PSQLPy
            pass

    async def get_connection(self) -> Connection:
        """
        Get a connection from the pool (manual management).

        WARNING: With manual management, you're responsible for connection lifecycle.
        Prefer using connection() context manager instead.

        Returns:
            Connection from the pool

        Raises:
            RuntimeError: If pool is not initialized
        """
        if not self._initialized or not self._pool:
            raise RuntimeError(
                "PostgreSQL manager not initialized. Call initialize() first."
            )

        return await self._pool.connection()

    async def execute(self, query: str, parameters: Optional[list] = None):
        """
        Execute a query using a connection from the pool.

        Convenience method for simple queries.

        Args:
            query: SQL query with $1, $2, ... placeholders
            parameters: Query parameters as list

        Returns:
            Query result

        Example:
            result = await manager.execute(
                "SELECT * FROM users WHERE email = $1",
                ["user@example.com"]
            )
        """
        async with self.connection() as conn:
            return await conn.execute(query, parameters or [])

    async def execute_many(self, query: str, parameters_list: list[list]):
        """
        Execute a query multiple times with different parameters.

        Useful for batch inserts.

        Args:
            query: SQL query
            parameters_list: List of parameter lists

        Returns:
            List of query results

        Example:
            results = await manager.execute_many(
                "INSERT INTO users (name, email) VALUES ($1, $2)",
                [
                    ["Alice", "alice@example.com"],
                    ["Bob", "bob@example.com"],
                    ["Charlie", "charlie@example.com"]
                ]
            )
        """
        async with self.connection() as conn:
            results = []
            for parameters in parameters_list:
                result = await conn.execute(query, parameters)
                results.append(result)
            return results

    async def verify_connection(self) -> bool:
        """
        Verify database connection is working.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            async with self.connection() as conn:
                await conn.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Connection verification failed: {e}")
            return False
