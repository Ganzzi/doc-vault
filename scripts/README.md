# DocVault Database Management Scripts

Utility scripts for managing the DocVault v2.0 database.

## Scripts

### `run_migration.py`
**Purpose:** Initialize or migrate the database

**Usage:**
```bash
python scripts/run_migration.py
```

**What it does:**
1. Detects current database version (empty, v1, or v2)
2. If v1 exists: Migrates to v2
3. If empty: Creates fresh v2 schema
4. If v2 exists: Skips (already initialized)

**Exit codes:**
- 0: Success
- 1: Failed

---

### `check_tables.py`
**Purpose:** List all tables in the database

**Usage:**
```bash
python scripts/check_tables.py
```

**Output:**
```
Tables in public schema:
  - agents
  - documents
  - document_versions
  - document_acl
  - organizations
  - document_tags
```

---

### `verify_schema.py`
**Purpose:** Verify v2 schema structure and constraints

**Usage:**
```bash
python scripts/verify_schema.py
```

**Output:**
- All tables and their columns
- Data types for each column
- All indexes and their configurations

**Useful for:**
- Validating schema after migrations
- Checking if new columns were added
- Verifying indexes exist

---

### `reset_db.py`
**Purpose:** DANGEROUS - Drop all tables and reset database

**Usage:**
```bash
python scripts/reset_db.py
```

**WARNING:** This will:
- Drop all tables
- Drop the public schema
- Recreate an empty public schema
- Destroy all data

**Use cases:**
- Starting fresh for testing
- Cleaning up corrupted database
- Testing migration from empty state

---

## Quick Workflow

### Fresh v2 Database Setup
```bash
# 1. Verify containers are running
docker ps

# 2. Initialize database
python scripts/run_migration.py

# 3. Verify setup
python scripts/check_tables.py
python scripts/verify_schema.py
```

### Database Reset (Testing)
```bash
# 1. Reset (WARNING: Deletes all data)
python scripts/reset_db.py

# 2. Re-initialize
python scripts/run_migration.py

# 3. Verify
python scripts/check_tables.py
```

### Troubleshooting
```bash
# Check what tables exist
python scripts/check_tables.py

# Verify all columns and indexes
python scripts/verify_schema.py

# Try re-initialization
python scripts/reset_db.py
python scripts/run_migration.py
```

---

## Requirements

- Python 3.10+
- Virtual environment with dependencies installed:
  ```bash
  .venv/Scripts/pip install psqlpy pydantic pydantic-settings
  ```
- PostgreSQL container running on localhost:5432
- Database credentials in environment or .env file:
  ```
  POSTGRES_HOST=localhost
  POSTGRES_PORT=5432
  POSTGRES_USER=postgres
  POSTGRES_PASSWORD=postgres
  POSTGRES_DB=doc_vault
  ```

---

## Notes

- All scripts use the PostgreSQLManager from src/doc_vault/database
- They respect the same configuration as the main DocVault SDK
- Scripts are safe to run multiple times (idempotent where possible)
- Run `run_migration.py` before using the SDK

---

## Maintenance

These scripts are auto-generated for Phase 1 of v2.0 development.
Update them if database management needs change.

Last updated: November 20, 2025
