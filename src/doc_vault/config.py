"""
Configuration management for DocVault SDK.

This module provides configuration classes using pydantic-settings
to load configuration from environment variables and validate them.
"""

import ssl
from typing import Any, Optional

from pydantic import Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class PostgresConfig(BaseSettings):
    """PostgreSQL database configuration."""

    model_config = SettingsConfigDict(
        env_prefix="POSTGRES_",
        env_file=".env",
        extra="ignore",
    )

    host: str = Field(default="localhost", description="PostgreSQL host")
    port: int = Field(default=5432, description="PostgreSQL port")
    user: str = Field(description="PostgreSQL username")
    password: str = Field(description="PostgreSQL password")
    db: str = Field(description="PostgreSQL database name")
    ssl: str = Field(
        default="disable",
        description="SSL mode for PostgreSQL connection",
        pattern="^(disable|prefer|require)$",
    )

    @field_validator("ssl")
    @classmethod
    def validate_ssl_mode(cls, v: str) -> str:
        """Validate SSL mode is one of the allowed values."""
        allowed = {"disable", "prefer", "require"}
        if v not in allowed:
            raise ValueError(f"SSL mode must be one of {allowed}, got {v}")
        return v

    @property
    def connection_string(self) -> str:
        """Generate PostgreSQL connection string."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"

    @property
    def ssl_context(self) -> "Optional[ssl.SSLContext]":
        """Get SSL context based on ssl mode."""
        if self.ssl == "disable":
            return None
        elif self.ssl == "prefer":
            # Allow SSL but don't require it
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            return context
        elif self.ssl == "require":
            # Require SSL with certificate verification
            return ssl.create_default_context()
        return None


class MinioConfig(BaseSettings):
    """MinIO/S3 storage configuration."""

    model_config = SettingsConfigDict(
        env_prefix="MINIO_",
        env_file=".env",
        extra="ignore",
    )

    endpoint: str = Field(description="MinIO/S3 endpoint URL")
    access_key: str = Field(description="MinIO/S3 access key")
    secret_key: str = Field(description="MinIO/S3 secret key")
    secure: bool = Field(default=False, description="Whether to use HTTPS")

    @property
    def endpoint_url(self) -> str:
        """Get the full endpoint URL with protocol."""
        protocol = "https" if self.secure else "http"
        return f"{protocol}://{self.endpoint}"


class DocVaultConfig(BaseSettings):
    """DocVault-specific configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    bucket_prefix: str = Field(
        default="doc-vault", description="Prefix for S3/MinIO buckets"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
    )
    debug: bool = Field(default=False, description="Enable debug mode")


class Config(BaseSettings):
    """Main configuration class for DocVault SDK."""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    postgres: PostgresConfig = Field(default_factory=PostgresConfig)
    minio: MinioConfig = Field(default_factory=MinioConfig)
    docvault: DocVaultConfig = Field(default_factory=DocVaultConfig)

    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        return cls()

    def __str__(self) -> str:
        """String representation (without sensitive data)."""
        return (
            f"Config(postgres_host={self.postgres.host}, "
            f"postgres_port={self.postgres.port}, "
            f"postgres_db={self.postgres.db}, "
            f"minio_endpoint={self.minio.endpoint}, "
            f"minio_secure={self.minio.secure}, "
            f"bucket_prefix={self.docvault.bucket_prefix})"
        )

    def __repr__(self) -> str:
        """Detailed string representation (without sensitive data)."""
        return self.__str__()
