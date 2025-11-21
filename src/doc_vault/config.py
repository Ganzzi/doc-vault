"""
Configuration management for DocVault SDK.

This module provides configuration classes using pydantic-settings
to support three initialization patterns:

1. **Direct Python Configuration** - Recommended for PyPI package users
   ```python
   from doc_vault import DocVaultSDK
   from doc_vault.config import Config

   config = Config(
       postgres_host="localhost",
       postgres_port=5432,
       postgres_user="postgres",
       postgres_password="password",
       postgres_db="doc_vault",
       minio_endpoint="localhost:9000",
       minio_access_key="minioadmin",
       minio_secret_key="minioadmin",
   )
   async with DocVaultSDK(config=config) as vault:
       # Use vault...
   ```

2. **Environment Variables** - Recommended for Docker/Kubernetes
   ```bash
   export POSTGRES_HOST=postgres
   export POSTGRES_PORT=5432
   export POSTGRES_USER=postgres
   export POSTGRES_PASSWORD=password
   export POSTGRES_DB=doc_vault
   export POSTGRES_SSL=disable
   export MINIO_ENDPOINT=minio:9000
   export MINIO_ACCESS_KEY=minioadmin
   export MINIO_SECRET_KEY=minioadmin
   export MINIO_SECURE=false
   export BUCKET_PREFIX=doc-vault
   export LOG_LEVEL=INFO
   ```
   ```python
   from doc_vault import DocVaultSDK
   async with DocVaultSDK() as vault:
       # Uses environment variables
   ```

3. **.env File Configuration** - Convenient for local development
   ```bash
   # .env (git-ignored)
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=password
   POSTGRES_DB=doc_vault
   POSTGRES_SSL=disable
   MINIO_ENDPOINT=localhost:9000
   MINIO_ACCESS_KEY=minioadmin
   MINIO_SECRET_KEY=minioadmin
   MINIO_SECURE=false
   BUCKET_PREFIX=doc-vault
   LOG_LEVEL=INFO
   ```
   ```python
   # Automatically loaded if python-dotenv is available
   from doc_vault import DocVaultSDK
   async with DocVaultSDK() as vault:
       # Uses .env file
   ```

Configuration Priority (first match wins):
1. Explicit Config object passed to DocVaultSDK
2. Environment variables (POSTGRES_*, MINIO_*, etc.)
3. .env file (if python-dotenv is available)
4. Hardcoded defaults
"""

import ssl
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Optional .env loading - only if python-dotenv is available
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # If python-dotenv is not installed, just use environment variables
    pass


class Config(BaseSettings):
    """Main configuration class for DocVault SDK.

    Supports three initialization patterns:
    - Direct Python instantiation
    - Environment variables
    - .env file (if python-dotenv is available)

    All configuration can be provided via environment variables with these prefixes:
    - POSTGRES_* for PostgreSQL connection
    - MINIO_* for MinIO/S3 storage
    """

    model_config = SettingsConfigDict(
        env_file=".env",  # Optional .env loading - only loaded if file exists
        extra="ignore",  # Ignore extra fields not defined in Config
    )

    # ==========================================================================
    # PostgreSQL Configuration
    # ==========================================================================

    postgres_host: str = Field(
        default="localhost",
        description="PostgreSQL server hostname",
    )
    postgres_port: int = Field(
        default=5432,
        description="PostgreSQL server port",
    )
    postgres_user: str = Field(
        description="PostgreSQL username",
    )
    postgres_password: str = Field(
        description="PostgreSQL password",
    )
    postgres_db: str = Field(
        description="PostgreSQL database name",
    )
    postgres_ssl: str = Field(
        default="disable",
        description="PostgreSQL SSL mode: 'disable', 'prefer', or 'require'",
    )

    # ==========================================================================
    # MinIO/S3 Storage Configuration
    # ==========================================================================

    minio_endpoint: str = Field(
        description="MinIO/S3 endpoint (e.g., 'localhost:9000' or 's3.amazonaws.com')",
    )
    minio_access_key: str = Field(
        description="MinIO/S3 access key ID",
    )
    minio_secret_key: str = Field(
        description="MinIO/S3 secret access key",
    )
    minio_secure: bool = Field(
        default=False,
        description="Whether to use HTTPS for MinIO/S3 connection",
    )

    # ==========================================================================
    # DocVault-specific Configuration
    # ==========================================================================

    bucket_prefix: str = Field(
        default="doc-vault",
        description="Prefix for S3/MinIO bucket names (buckets are named: {prefix}-org-{org_id})",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, ERROR, or CRITICAL",
    )

    # ==========================================================================
    # Validators
    # ==========================================================================

    @field_validator("postgres_ssl")
    @classmethod
    def validate_postgres_ssl(cls, v: str) -> str:
        """Validate PostgreSQL SSL mode."""
        allowed = {"disable", "prefer", "require"}
        if v not in allowed:
            raise ValueError(f"postgres_ssl must be one of {allowed}, got '{v}'")
        return v

    @field_validator("postgres_port")
    @classmethod
    def validate_postgres_port(cls, v: int) -> int:
        """Validate PostgreSQL port."""
        if not (1 <= v <= 65535):
            raise ValueError(f"postgres_port must be between 1 and 65535, got {v}")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in allowed:
            raise ValueError(f"log_level must be one of {allowed}, got '{v}'")
        return v.upper()

    @field_validator("minio_secure", mode="before")
    @classmethod
    def validate_minio_secure(cls, v: any) -> bool:
        """Validate and convert minio_secure to boolean."""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes")
        return bool(v)

    # ==========================================================================
    # Connection String Properties
    # ==========================================================================

    @property
    def postgres_connection_string(self) -> str:
        """Generate PostgreSQL connection string.

        Returns:
            PostgreSQL connection URL for psqlpy
        """
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def postgres_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Get SSL context based on postgres_ssl mode.

        Returns:
            ssl.SSLContext for the specified SSL mode, or None if SSL is disabled

        Raises:
            ValueError: If postgres_ssl mode is invalid
        """
        if self.postgres_ssl == "disable":
            return None
        elif self.postgres_ssl == "prefer":
            # Allow SSL but don't require it (don't verify certificate)
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            return context
        elif self.postgres_ssl == "require":
            # Require SSL with full certificate verification
            return ssl.create_default_context()
        else:
            raise ValueError(f"Invalid postgres_ssl mode: {self.postgres_ssl}")

    @property
    def minio_endpoint_url(self) -> str:
        """Get the full MinIO/S3 endpoint URL with protocol.

        Returns:
            Full URL (e.g., 'http://localhost:9000' or 'https://s3.amazonaws.com')
        """
        protocol = "https" if self.minio_secure else "http"
        return f"{protocol}://{self.minio_endpoint}"

    # ==========================================================================
    # Factory Methods
    # ==========================================================================

    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables and/or .env file.

        This is a convenience method for backward compatibility.
        You can also just call Config() directly.

        Returns:
            Config instance loaded from environment variables

        Example:
            ```python
            config = Config.from_env()
            ```
        """
        return cls()

    # ==========================================================================
    # String Representations
    # ==========================================================================

    def __str__(self) -> str:
        """String representation (without sensitive data)."""
        return (
            f"Config("
            f"postgres_host={self.postgres_host}, "
            f"postgres_port={self.postgres_port}, "
            f"postgres_db={self.postgres_db}, "
            f"postgres_ssl={self.postgres_ssl}, "
            f"minio_endpoint={self.minio_endpoint}, "
            f"minio_secure={self.minio_secure}, "
            f"bucket_prefix={self.bucket_prefix}, "
            f"log_level={self.log_level}"
            f")"
        )

    def __repr__(self) -> str:
        """Detailed string representation (without sensitive data)."""
        return self.__str__()
