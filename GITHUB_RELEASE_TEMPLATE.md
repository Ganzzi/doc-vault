## DocVault SDK v1.0.0 - Initial Production Release

**Release Date:** October 23, 2025

### 🎉 Highlights

DocVault SDK v1.0.0 is ready for production! This release includes a complete, scalable document management system with access control, versioning, and multi-organization support.

### ✨ What's New

**Complete SDK Implementation**
- Document management: upload, download, update, delete
- Role-based access control (READ, WRITE, DELETE, SHARE, ADMIN)
- Document versioning with restore functionality
- Multi-organization isolation with bucket-per-org architecture
- Full-text search powered by PostgreSQL
- MinIO/S3 integration for binary file storage

**Architecture**
- Async-first design using psqlpy
- Service layer for business logic
- Repository pattern for data access
- Proper error handling and validation
- Full type safety with mypy

**Configuration System (Latest Refactoring)**
- Three flexible initialization patterns:
  * Direct Python Configuration (recommended for PyPI)
  * Environment Variables (recommended for Docker/Kubernetes)
  * .env File Configuration (convenient for local development)
- Simplified flat configuration structure
- Optional python-dotenv dependency for production

### 📦 Installation

```bash
# Via PyPI
pip install doc-vault

# With development tools
pip install doc-vault[dev]

# From source
git clone https://github.com/docvault/doc-vault.git
cd doc-vault
uv sync
```

### 🚀 Quick Start

```python
import asyncio
from doc_vault import DocVaultSDK

async def main():
    async with DocVaultSDK() as vault:
        # Upload a document
        document = await vault.upload(
            file_path="./report.pdf",
            name="Q4 Financial Report",
            organization_id="org-123",
            agent_id="agent-456"
        )
        
        # Grant access
        await vault.share(
            document_id=document.id,
            agent_id="agent-789",
            permission="READ",
            granted_by="agent-456"
        )
        
        # Download document
        content = await vault.download(
            document_id=document.id,
            agent_id="agent-789"
        )

asyncio.run(main())
```

### 🔧 Requirements

- Python 3.10+
- PostgreSQL 14+
- MinIO or AWS S3
- 512MB+ RAM

### 📚 Documentation

- **[README](https://github.com/docvault/doc-vault/blob/main/README.md)** - Complete guide with examples
- **[Examples](https://github.com/docvault/doc-vault/tree/main/examples)** - Real-world usage patterns
- **[API Reference](https://github.com/docvault/doc-vault/blob/main/docs/API.md)** - Full API documentation
- **[Development Guide](https://github.com/docvault/doc-vault/blob/main/DEVELOPMENT.md)** - Local setup and testing

### 📊 Quality Metrics

- ✅ 66%+ test coverage
- ✅ Type-safe with mypy
- ✅ Full async support
- ✅ Production-ready

### 🐛 Known Limitations

- PDF processing features planned for v2.0
- Semantic search requires pgvector extension
- Bulk operations not yet implemented

### 🙏 Credits

Built with:
- [psqlpy](https://github.com/psycopg/psycopg) - High-performance async PostgreSQL
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation
- [MinIO](https://min.io/) - S3-compatible storage

### 📝 Changelog

See [CHANGELOG.md](https://github.com/docvault/doc-vault/blob/main/CHANGELOG.md) for detailed version history.

### 🔗 Links

- **Repository:** https://github.com/docvault/doc-vault
- **PyPI:** https://pypi.org/project/doc-vault/
- **Issues:** https://github.com/docvault/doc-vault/issues
- **Email:** team@docvault.dev

---

**Ready for production use!** 🎉
