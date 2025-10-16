# Development Guide

This guide covers setting up a local development environment for DocVault SDK.

## 📋 Prerequisites

- Python 3.10 or higher
- uv package manager
- Docker and Docker Compose (for local services)
- Git

## 🚀 Quick Setup

### 1. Clone and Install

```bash
# Clone repository
git clone https://github.com/docvault/doc-vault.git
cd doc-vault

# Install uv (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

### 2. Start Local Services

DocVault requires both PostgreSQL and MinIO for full functionality.

#### Using Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# Or start specific services
docker-compose up -d postgres minio

# Check service status
docker-compose ps

# View logs
docker-compose logs postgres
docker-compose logs minio

# Stop services
docker-compose down

# Stop and remove volumes (WARNING: destroys data)
docker-compose down -v
```

#### Service URLs
- **PostgreSQL**: `localhost:5432`
- **MinIO API**: `localhost:9000`
- **MinIO Console**: `http://localhost:9001`
  - Username: `minioadmin`
  - Password: `minioadmin`

#### Manual Docker Setup

```bash
# PostgreSQL with pgvector
docker run -d \
  --name docvault-postgres \
  -p 5432:5432 \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=doc_vault \
  tensorchord/vchord-suite:pg16-latest

# MinIO
docker run -d \
  --name docvault-minio \
  -p 9000:9000 \
  -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ":9001"
```

### 3. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your local settings
# Default settings should work with Docker containers above
```

### 4. Initialize Database

```bash
# Create database schema
uv run python -m doc_vault.database.init_db

# Verify connection
uv run python -c "from doc_vault.config import Config; c = Config(); print('Config loaded successfully')"
```

### 5. Run Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov --cov-report=html

# Run specific tests
uv run pytest tests/test_config.py -v
```

## 🏗️ Project Structure

```
doc-vault/
├── src/doc_vault/              # Main package
│   ├── __init__.py            # Package exports
│   ├── config.py              # Configuration management
│   ├── core.py                # Main SDK API
│   ├── exceptions.py          # Custom exceptions
│   ├── database/              # Database layer
│   │   ├── __init__.py
│   │   ├── postgres_manager.py
│   │   ├── init_db.py
│   │   ├── repositories/      # Data access layer
│   │   └── schemas/           # Pydantic models
│   ├── services/              # Business logic layer
│   ├── storage/               # Storage layer
│   └── sql/                   # SQL scripts
├── tests/                     # Test suite
├── examples/                  # Usage examples
├── docs/                      # Documentation
├── pyproject.toml             # Project configuration
├── uv.lock                    # Dependency lock file
├── README.md                  # Main documentation
├── CONTRIBUTING.md            # Contributing guide
├── DEVELOPMENT.md             # This file
├── .env.example               # Environment template
├── .gitignore                 # Git ignore rules
└── docker-compose.yml         # Local development stack
```

## 🔧 Development Tools

### Code Quality

```bash
# Format code
uv run black src/

# Lint code
uv run ruff check src/

# Fix linting issues
uv run ruff check src/ --fix

# Type checking
uv run mypy src/

# Run all quality checks
uv run pre-commit run --all-files
```

### Testing

```bash
# Run tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_config.py

# Run tests with coverage
uv run pytest --cov=src/doc_vault --cov-report=term-missing

# Generate HTML coverage report
uv run pytest --cov=src/doc_vault --cov-report=html
open htmlcov/index.html  # View report in browser

# Run slow tests only
uv run pytest -m slow

# Run tests in parallel (if pytest-xdist installed)
uv run pytest -n auto
```

### Pre-commit Hooks

```bash
# Install hooks
pre-commit install

# Run on all files
pre-commit run --all-files

# Run specific hook
pre-commit run black --all-files
```

## 🗄️ Database Development

### Local PostgreSQL Setup

```bash
# Using Docker
docker run -d \
  --name docvault-postgres \
  -p 5432:5432 \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=doc_vault \
  postgres:15

# Connect to database
psql -h localhost -U postgres -d doc_vault
```

### Database Schema

```bash
# View current schema
psql -h localhost -U postgres -d doc_vault -c "\dt"

# View table structure
psql -h localhost -U postgres -d doc_vault -c "\d documents"

# Reset database (CAUTION: destroys data)
uv run python -m doc_vault.database.init_db --reset
```

### Database Migrations

When schema changes are needed:

1. Update SQL files in `src/doc_vault/sql/`
2. Update Pydantic models in `src/doc_vault/database/schemas/`
3. Update repositories if needed
4. Test with existing data
5. Update migration scripts if necessary

## ☁️ Storage Development

### Local MinIO Setup

```bash
# Using Docker
docker run -d \
  --name docvault-minio \
  -p 9000:9000 \
  -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ":9001"

# Access MinIO Console
# URL: http://localhost:9001
# Username: minioadmin
# Password: minioadmin
```

### Storage Testing

```bash
# List buckets
curl -X GET "http://localhost:9000/" \
  -H "Authorization: AWS4-HMAC-SHA256 Credential=minioadmin/"

# Create test bucket
curl -X PUT "http://localhost:9000/test-bucket" \
  -H "Authorization: AWS4-HMAC-SHA256 Credential=minioadmin/"
```

## 🔍 Debugging

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Or in .env
LOG_LEVEL=DEBUG
```

### Debug Database Queries

```python
# Enable SQL query logging
import logging
logging.getLogger('psqlpy').setLevel(logging.DEBUG)
```

### Debug API Calls

```python
# Enable HTTP request logging
import logging
logging.getLogger('urllib3').setLevel(logging.DEBUG)
```

## 📊 Performance Testing

### Benchmarking

```bash
# Run performance tests
uv run pytest tests/ -k "perf" -v

# Profile specific function
uv run python -m cProfile -s time your_script.py
```

### Memory Usage

```bash
# Check memory usage
uv run python -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB')
"
```

## 🚀 Deployment

### Building Distribution

```bash
# Build wheel and source distribution
uv build

# Install locally for testing
uv pip install -e .
```

### Docker Development

```bash
# Build development image
docker build -f Dockerfile.dev -t docvault:dev .

# Run development container
docker run -it --rm \
  -v $(pwd):/app \
  -p 8000:8000 \
  docvault:dev
```

## 📚 Documentation

### Building Docs

```bash
# Install docs dependencies
uv sync --extra docs

# Build documentation
cd docs
make html
open _build/html/index.html
```

### API Documentation

```bash
# Generate API docs
uv run sphinx-apidoc -f -o docs/api src/doc_vault

# Build with API docs
cd docs && make html
```

## 🤝 Contributing Workflow

1. **Create Issue**: Start with a GitHub issue
2. **Create Branch**: `git checkout -b feature/your-feature`
3. **Make Changes**: Follow code standards
4. **Write Tests**: Add comprehensive tests
5. **Update Docs**: Keep documentation current
6. **Run Checks**: `uv run pre-commit run --all-files`
7. **Create PR**: Submit pull request
8. **Code Review**: Address feedback
9. **Merge**: Squash and merge

## 🆘 Troubleshooting

### Common Issues

**Import Error**: `ModuleNotFoundError: No module named 'doc_vault'`
```bash
# Install in development mode
uv pip install -e .
```

**Database Connection Failed**
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Check connection
psql -h localhost -U postgres -d doc_vault -c "SELECT 1;"
```

**MinIO Connection Failed**
```bash
# Check if MinIO is running
docker ps | grep minio

# Check MinIO console at http://localhost:9001
```

**Tests Failing**
```bash
# Run with verbose output
uv run pytest -v -s

# Check test database
psql -h localhost -U postgres -d doc_vault_test -c "\dt"
```

### Getting Help

- Check [GitHub Issues](https://github.com/docvault/doc-vault/issues)
- Review [Contributing Guide](./CONTRIBUTING.md)
- Ask in [GitHub Discussions](https://github.com/docvault/doc-vault/discussions)

## 📋 Checklist

Before submitting changes:

- [ ] Code follows style guidelines (`black`, `ruff`)
- [ ] Type hints are correct (`mypy`)
- [ ] Tests pass (`pytest`)
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (if needed)
- [ ] Pre-commit hooks pass
- [ ] No sensitive data committed
- [ ] Commit messages follow conventional format

## 🏗️ Development Progress

### Phase 5: Service Layer ✅ COMPLETED (Oct 16, 2025)

**Implemented:**
- ✅ **DocumentService**: Complete document lifecycle management
  - Upload documents with automatic versioning
  - Download with permission checking
  - Metadata updates and tag management
  - Soft and hard delete operations
  - Replace document files with new versions
  - List and search documents with filtering
- ✅ **AccessService**: Permission and ACL management
  - Grant/revoke document access
  - Check permissions with expiration handling
  - List accessible documents for agents
  - Get document permissions by agent
- ✅ **VersionService**: Document version management
  - List all versions of a document
  - Get specific version information
  - Restore previous versions
  - Version history tracking
- ✅ **Database Schema**: Complete PostgreSQL schema
  - All tables (organizations, agents, documents, versions, ACL, tags)
  - Indexes for performance optimization
  - Triggers for auto-updating timestamps and search vectors
  - Full-text search support with tsvector
- ✅ **Repository Fixes**: Updated create methods
  - Fixed UUID parameter handling for psqlpy
  - Proper type conversion for database operations
  - Direct INSERT queries instead of model instantiation
- ✅ **Integration Tests**: Comprehensive test suite
  - 31 test cases covering all service operations
  - Test fixtures for database and storage setup
  - Tests for success and failure scenarios

**Status:** Service layer fully implemented and committed. Tests written but fixtures need refinement for full CI/CD integration.

**Next Steps:**
- Phase 6: SDK API Layer - Public-facing SDK interface
- Resolve test fixture configuration issues
- Add end-to-end integration tests