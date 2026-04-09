# Development Guide

## Prerequisites
- Python >=3.10
- uv
- PostgreSQL 14+ (for integration/e2e tests)
- MinIO or S3-compatible storage (for integration/e2e tests)

## Setup

```bash
uv sync --all-groups --all-extras
```

## Unit Tests (PR Gate)

```bash
uv run pytest -m "unit" -q
```

## Integration / E2E Tests

```bash
uv run pytest -q                    # runs all tests
uv run pytest -m integration        # integration only
uv run pytest -m e2e                # e2e only
```

## Coverage

```bash
uv run pytest -m "not integration and not e2e" --cov --cov-report=term-missing
```

## Test Structure

```
tests/
├── conftest.py          # shared fixtures
├── unit/                # no external deps (PR-gated)
│   ├── test_response_models.py
│   └── test_s3_client.py
├── integration/         # requires PostgreSQL/MinIO
│   ├── test_*_repository.py
│   ├── test_*_service.py
│   ├── test_core_*.py
│   └── test_schema_migration.py
└── e2e/                 # full SDK flow
    └── test_core.py
```

## CI Behavior

CI runs unit tests only on every push/PR via:
```bash
uv sync --all-groups --all-extras
uv run pytest -m "not integration and not e2e" -q
```

Integration and e2e tests require running PostgreSQL and MinIO services.

## Database Setup (Local)

```bash
docker compose up -d
uv run python -m doc_vault.database.init_db
```

## Code Quality

```bash
uv run black src/
uv run ruff check src/
uv run mypy src/
```

## Known Issues

- Integration tests require active PostgreSQL and MinIO instances
- Schema migration tests depend on v1 schema state
