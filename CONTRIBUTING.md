# Contributing to DocVault

Thank you for your interest in contributing to DocVault! We welcome contributions from the community.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Submitting Changes](#submitting-changes)
- [Community](#community)

## 🤝 Code of Conduct

This project follows a code of conduct to ensure a welcoming environment for all contributors. By participating, you agree to:

- Be respectful and inclusive
- Focus on constructive feedback
- Accept responsibility for mistakes
- Show empathy towards other contributors
- Help create a positive community

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher
- uv package manager
- Git

### Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/your-username/doc-vault.git
   cd doc-vault
   ```

2. **Install uv** (if not already installed)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Install Dependencies**
   ```bash
   uv sync
   ```

4. **Activate Virtual Environment**
   ```bash
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

5. **Install Pre-commit Hooks**
   ```bash
   pre-commit install
   ```

6. **Verify Setup**
   ```bash
   uv run python -c "import doc_vault; print('Setup successful!')"
   ```

## 🔄 Development Workflow

### 1. Choose an Issue

- Check [GitHub Issues](https://github.com/docvault/doc-vault/issues) for open tasks
- Look for issues labeled `good first issue` or `help wanted`
- Comment on the issue to indicate you're working on it

### 2. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-number-description
```

### 3. Make Changes

- Write clear, focused commits
- Follow the [code standards](#code-standards)
- Add tests for new functionality
- Update documentation as needed

### 4. Test Your Changes

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov

# Run specific tests
uv run pytest tests/test_specific.py

# Run quality checks
uv run pre-commit run --all-files
```

### 5. Update Documentation

- Update README.md if needed
- Add docstrings to new functions
- Update type hints
- Add examples for new features

## 📏 Code Standards

### Python Style

- Follow [PEP 8](https://pep8.org/) style guidelines
- Use [Black](https://black.readthedocs.io/) for code formatting
- Use [Ruff](https://beta.ruff.rs/docs/) for linting
- Use [MyPy](https://mypy.readthedocs.io/) for type checking

### Code Quality Tools

All code must pass these checks:

```bash
# Format code
uv run black src/

# Lint code
uv run ruff check src/

# Type check
uv run mypy src/

# Run all checks
uv run pre-commit run --all-files
```

### Commit Messages

Follow conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Testing
- `chore`: Maintenance

Examples:
```
feat(auth): add JWT token support
fix(api): handle null values in response
docs(readme): update installation instructions
```

## 🧪 Testing

### Test Structure

- Unit tests in `tests/` directory
- Test files named `test_*.py`
- Use `pytest` framework
- Write async tests with `pytest-asyncio`

### Writing Tests

```python
import pytest
from doc_vault import DocVaultSDK

class TestDocumentService:
    @pytest.mark.asyncio
    async def test_upload_document(self, vault: DocVaultSDK):
        # Test implementation
        pass

    @pytest.mark.asyncio
    async def test_download_document(self, vault: DocVaultSDK):
        # Test implementation
        pass
```

### Test Coverage

- Aim for >90% code coverage
- Cover both success and error paths
- Test edge cases and boundary conditions

## 📚 Documentation

### Code Documentation

- Add docstrings to all public functions and classes
- Use Google-style docstrings
- Include type hints for all parameters and return values

```python
def upload_document(
    self,
    file_path: str,
    name: str,
    organization_id: str,
    agent_id: str,
    description: Optional[str] = None
) -> Document:
    """Upload a document to the vault.

    Args:
        file_path: Path to the file to upload
        name: Display name for the document
        organization_id: ID of the organization
        agent_id: ID of the uploading agent
        description: Optional description of the document

    Returns:
        The uploaded document metadata

    Raises:
        ValidationError: If input validation fails
        PermissionDeniedError: If agent lacks upload permission
    """
```

### API Documentation

- Keep README.md up to date
- Add examples for new features
- Update configuration documentation

## 📤 Submitting Changes

### Pull Request Process

1. **Ensure all checks pass**
   ```bash
   uv run pre-commit run --all-files
   uv run pytest --cov
   ```

2. **Update CHANGELOG.md** (if applicable)
   - Add entry under "Unreleased" section
   - Follow [Keep a Changelog](https://keepachangelog.com/) format

3. **Create Pull Request**
   - Use descriptive title
   - Fill out PR template
   - Reference related issues
   - Add screenshots for UI changes

4. **Code Review**
   - Address reviewer feedback
   - Make requested changes
   - Keep conversations focused

5. **Merge**
   - Squash commits when merging
   - Use "Squash and merge" for clean history

### PR Checklist

- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (if needed)
- [ ] Commit messages follow conventional format
- [ ] PR description is clear and detailed

## 🌐 Community

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and ideas
- **Discord**: Real-time chat (coming soon)

### Getting Help

- Check existing issues and documentation first
- Use GitHub Discussions for questions
- Be specific when reporting bugs

### Recognition

Contributors are recognized in:
- CHANGELOG.md for significant contributions
- GitHub's contributor insights
- Release notes

## 📋 Additional Resources

- [Development Guide](./DEVELOPMENT.md) - Detailed development setup
- [API Documentation](https://docvault.readthedocs.io/) - Full API reference
- [Architecture Overview](./docs/plan/DocVault-implementation-plan.md) - System design
- [PSQLPy Guide](./docs/psqlpy-complete-guide.md) - Database driver documentation

Thank you for contributing to DocVault! 🎉