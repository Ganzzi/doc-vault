"""
Core DocVault SDK implementation.

This module contains the main DocVaultSDK class that provides
the high-level API for document management.
"""

from typing import Optional

from .config import Config


class DocVaultSDK:
    """
    Main DocVault SDK class for document management.

    This class provides the high-level API for uploading, downloading,
    and managing documents with role-based access control.
    """

    def __init__(self, config: Optional[Config] = None) -> None:
        """
        Initialize the DocVault SDK.

        Args:
            config: Configuration object. If None, loads from environment.
        """
        self.config = config or Config.from_env()

    async def __aenter__(self) -> "DocVaultSDK":
        """Async context manager entry."""
        # TODO: Initialize database connections and storage backends
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        # TODO: Clean up connections
        pass

    def __str__(self) -> str:
        """String representation."""
        return f"DocVaultSDK(config={self.config})"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return self.__str__()
