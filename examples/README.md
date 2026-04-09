# DocVault SDK Examples

This directory contains comprehensive examples demonstrating the DocVault SDK features and usage patterns.

## Examples Overview

### `basic_usage.py`
Complete end-to-end demonstration of core DocVault SDK functionality:
- Organization and agent registration
- Document upload and download
- Metadata management
- Document search
- Access control basics
- Document versioning introduction

**Run with:**
```bash
python examples/basic_usage.py
```

### `access_control.py`
Advanced access control features demonstration:
- Permission levels (READ, WRITE, DELETE, SHARE)
- Document sharing with specific permissions
- Permission validation and enforcement
- Access revocation
- Role-based access control patterns

**Run with:**
```bash
python examples/access_control.py
```

### `versioning.py`
Document versioning capabilities:
- Creating multiple document versions
- Version history tracking
- Version-specific downloads
- Restoring previous versions
- Change descriptions and metadata
- Version numbering and timestamps

**Run with:**
```bash
python examples/versioning.py
```

### `multi_org.py`
Multi-organization usage patterns:
- Managing multiple organizations
- Organization-level data isolation
- Cross-organization document sharing
- Agent membership across organizations
- Complex permission scenarios

**Run with:**
```bash
python examples/multi_org.py
```

## Prerequisites

Before running the examples, ensure you have:

1. **Environment Setup**: Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   # Edit .env with your database and storage credentials
   ```

2. **Services Running**: Start the required services:
   ```bash
   docker-compose up -d
   ```

3. **Package Installation**: Install DocVault in development mode:
   ```bash
   pip install -e .
   ```

## Configuration

The examples use environment variables for configuration. Key settings:

- `POSTGRES_HOST`: Database host (default: localhost)
- `POSTGRES_PORT`: Database port (default: 5433)
- `POSTGRES_DB`: Database name
- `POSTGRES_USER`: Database user
- `POSTGRES_PASSWORD`: Database password
- `MINIO_ENDPOINT`: Object storage endpoint
- `MINIO_ACCESS_KEY`: Storage access key
- `MINIO_SECRET_KEY`: Storage secret key
- `MINIO_BUCKET`: Storage bucket name

## Example Structure

Each example follows this pattern:

1. **Setup**: Initialize SDK and create test data
2. **Core Demonstration**: Show the main features
3. **Verification**: Confirm operations worked correctly
4. **Cleanup**: Remove test data

## Error Handling

The examples include comprehensive error handling and will display:
- ✅ Success messages for completed operations
- ❌ Error messages with details for failed operations
- Progress indicators throughout execution

## Learning Path

Start with `basic_usage.py` to understand core concepts, then progress to:

1. `basic_usage.py` - Core SDK usage
2. `access_control.py` - Permission management
3. `versioning.py` - Document versioning
4. `multi_org.py` - Multi-organization scenarios

## Integration Testing

These examples serve as integration tests and demonstrate:
- Real-world usage patterns
- Error conditions and recovery
- Performance characteristics
- Memory management with async context managers

## Troubleshooting

**Common Issues:**

1. **Import Error**: Ensure DocVault is installed (`pip install -e .`)
2. **Database Connection**: Verify PostgreSQL is running (`docker-compose ps`)
3. **Storage Connection**: Verify MinIO is running and accessible
4. **Permissions**: Check file permissions for temporary files

**Debug Mode**: Set environment variable `DEBUG=1` for verbose logging.

## Contributing

When adding new examples:
- Follow the existing code style and patterns
- Include comprehensive docstrings
- Add error handling for all operations
- Update this README with the new example
- Test with both success and failure scenarios