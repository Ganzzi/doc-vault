"""
Database layer for DocVault SDK.

This package contains database connection management, Pydantic schemas,
and repository classes for data access.
"""

from . import repositories, schemas
from .postgres_manager import PostgreSQLManager

__all__ = [
    "PostgreSQLManager",
    "repositories",
    "schemas",
]
