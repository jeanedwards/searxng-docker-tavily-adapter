# 🤖 Agent Guidelines for SearXNG Tavily Adapter

This document provides guidelines for AI agents (Claude, ChatGPT, Cursor AI) working with this project.

## 🎯 Quick Start for AI Agents

This project supports TWO development workflows:

1. **Docker (Production)**: Full stack with SearXNG + Redis + Adapter
2. **Local Development (uv)**: Modern Python package manager for fast local iteration

## 📂 Project Structure

### Core Application
- `simple_tavily_adapter/main.py` - FastAPI application entry point
- `simple_tavily_adapter/routes.py` - API endpoint handlers
- `simple_tavily_adapter/services.py` - Business logic (search, scraping)
- `simple_tavily_adapter/models.py` - Pydantic request/response models
- `simple_tavily_adapter/config_loader.py` - Configuration loader
- `simple_tavily_adapter/utils.py` - Utility functions

### Configuration
- `config.yaml` - Main configuration (secrets, URLs, limits)
- `config.example.yaml` - Configuration template
- `config.azure.yaml` - Azure-specific configuration
- `pyproject.toml` - **NEW**: Python project configuration and dependencies
- `.python-version` - **NEW**: Python version specification (3.11)

### Docker & Deployment
- `docker-compose.yaml` - Service orchestration
- `simple_tavily_adapter/Dockerfile` - Adapter container build
- `.github/workflows/azure-deploy.yml` - Azure deployment workflow

### Development Tools
- `Makefile` - **NEW**: Convenient development commands
- `setup-local.sh` - **NEW**: Automated setup script (macOS/Linux)
- `setup-local.ps1` - **NEW**: Automated setup script (Windows)
- `simple_tavily_adapter/requirements.txt` - Docker dependencies (kept for compatibility)

### Documentation
- `README.md` - Main documentation (Russian)
- `LOCAL_DEVELOPMENT.md` - **NEW**: Local development guide with uv
- `UV_CHEATSHEET.md` - **NEW**: Quick reference for uv commands
- `UV_MIGRATION_NOTES.md` - **NEW**: Migration notes and FAQ
- `CONFIG_SETUP.md` - Configuration guide
- `AZURE_DEPLOYMENT.md` - Azure deployment guide
- `TESTING_RAW_CONTENT.md` - Web scraping testing guide
- `AGENTS.md` - This file

## 🚀 Basic Commands for Agents

### Local Development (Modern - Recommended)

```bash
# One-time setup
./setup-local.sh       # macOS/Linux
.\setup-local.ps1      # Windows

# Or manual setup
uv sync                # Install dependencies
cp config.example.yaml config.yaml
# Edit config.yaml to set secret_key

# Run adapter with hot-reload
uv run uvicorn simple_tavily_adapter.main:app --reload

# Common tasks (using Makefile)
make help              # Show all available commands
make setup             # Automated setup
make run               # Run with hot-reload
make test              # Run tests
make format            # Format code
make lint              # Check code quality
make docker-up         # Start Docker services (SearXNG + Redis)
```

### Local Development (Traditional - pip)

```bash
# Setup
cd simple_tavily_adapter
pip install -r requirements.txt
crawl4ai-setup         # Install Playwright browsers

# Run
python main.py

# Test
python test_client.py
```

### Docker (Full Stack)

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f adapter

# Stop all services
docker compose down
```

## 🛠️ Common Agent Tasks

### Adding a New Dependency

**Modern way (uv):**
```bash
uv add package-name
# Updates pyproject.toml and uv.lock automatically
```

**Traditional way (for Docker):**
```bash
# Edit simple_tavily_adapter/requirements.txt
# Add: package-name>=version
# Then rebuild Docker image
docker compose build adapter
```

### Running Tests

```bash
# With uv
uv run pytest

# With make
make test

# Traditional
pytest
```

### Code Quality

```bash
# Format code
uv run ruff format .
# or
make format

# Check linting
uv run ruff check .
# or
make lint

# Fix auto-fixable issues
uv run ruff check --fix .
```

### Testing API Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Search endpoint
curl -X POST "http://localhost:8000/search" \
     -H "Content-Type: application/json" \
     -d '{"query": "test search", "max_results": 3}'

# Extract endpoint
curl -X POST "http://localhost:8000/extract" \
     -H "Content-Type: application/json" \
     -d '{"urls": ["https://example.com"], "format": "markdown"}'

# Using test client
uv run python simple_tavily_adapter/test_client.py
```

## 📝 Code Modification Guidelines

### When Modifying Code

1. **Always check existing patterns** - Look at similar code first
2. **Add comments** - Explain WHY, not just WHAT (Google Python style)
3. **Use type hints** - All functions should have type annotations
4. **Keep functions small** - Break complex logic into smaller functions
5. **Test changes** - Run the adapter locally before committing

### File Size Limits

- Keep files under 200 lines when possible
- If a file grows too large, split into multiple modules
- Example: Split `services.py` into `search_service.py` and `scraper_service.py`

### Naming Conventions

- **Functions/Variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private functions**: `_leading_underscore`

### Error Handling

```python
# Always log errors with context
logger.error(f"Failed to fetch URL {url}: {str(e)}")

# Use specific exceptions
except aiohttp.ClientError as e:
    # Handle specific error
    pass

# Return meaningful error messages
return {"error": "Detailed error message", "status": "failed"}
```

## 🐛 Debugging

### View Adapter Logs

```bash
# Docker
docker compose logs -f adapter

# Local (output to console)
uv run uvicorn simple_tavily_adapter.main:app --reload --log-level debug
```

### Check SearXNG Connection

```bash
# Test SearXNG directly
curl "http://localhost:8999/search?q=test&format=json"

# Check if services are running
docker compose ps
```

### Common Issues

1. **Import errors**: Make sure dependencies are installed (`uv sync`)
2. **Port already in use**: Change port in `config.yaml` or stop conflicting service
3. **SearXNG not responding**: Wait 10-20 seconds after `docker compose up`
4. **Config not loading**: Ensure `config.yaml` exists and has valid YAML syntax

## 📦 Dependency Management

### Understanding the Setup

- **`pyproject.toml`**: Source of truth for dependencies (development)
- **`uv.lock`**: Locked versions (auto-generated, commit to git)
- **`simple_tavily_adapter/requirements.txt`**: Used by Docker only
- **`.venv/`**: Virtual environment (auto-created by uv, do not commit)

### When to Update requirements.txt

Only update `simple_tavily_adapter/requirements.txt` when:
1. Docker build needs new package
2. After adding dependency with `uv add`
3. Manually: Copy from `pyproject.toml` dependencies section

### Keeping Files in Sync

```bash
# After adding dependencies with uv
uv add new-package

# Update requirements.txt for Docker
uv pip freeze > simple_tavily_adapter/requirements.txt
```

## 🔄 Git Workflow

### Files to Commit

✅ **Always commit:**
- Source code changes
- `pyproject.toml` (if dependencies changed)
- `uv.lock` (if dependencies changed)
- `simple_tavily_adapter/requirements.txt` (if dependencies changed)
- Documentation updates

❌ **Never commit:**
- `config.yaml` (contains secrets)
- `.venv/` (virtual environment)
- `__pycache__/` (Python cache)
- `*.pyc` (compiled Python)
- `.DS_Store` (macOS)

### Commit Message Format

```
feat: add new feature
fix: fix bug in scraper
docs: update README with uv instructions
refactor: simplify search logic
test: add tests for extract endpoint
chore: update dependencies
```

## 🧪 Testing Strategy

### Test Levels

1. **Unit tests** - Test individual functions
2. **Integration tests** - Test API endpoints
3. **Manual tests** - Use `test_client.py` or curl

### Writing Tests

```python
# tests/test_services.py
import pytest
from simple_tavily_adapter.services import SearchService

@pytest.mark.asyncio
async def test_search_service():
    """Test search functionality."""
    service = SearchService()
    results = await service.search("test query")
    assert len(results) > 0
    assert "url" in results[0]
```

### Running Tests

```bash
# All tests
uv run pytest

# Specific test file
uv run pytest tests/test_services.py

# Specific test
uv run pytest tests/test_services.py::test_search_service

# With verbose output
uv run pytest -v

# With coverage
uv run pytest --cov=simple_tavily_adapter
```

## 🚀 Deployment

### Local Docker

```bash
docker compose up -d
```

### Azure Container Apps

See `.github/workflows/azure-deploy.yml` and `AZURE_DEPLOYMENT.md`

## 📖 Additional Resources

- **Local Development**: See `LOCAL_DEVELOPMENT.md` for detailed guide
- **uv Commands**: See `UV_CHEATSHEET.md` for quick reference
- **Configuration**: See `CONFIG_SETUP.md` for config options
- **Migration Notes**: See `UV_MIGRATION_NOTES.md` for changes

## 🤖 Tips for AI Agents

1. **Read relevant docs first** - Check LOCAL_DEVELOPMENT.md for setup questions
2. **Use uv for local dev** - It's faster and more reliable than pip
3. **Keep Docker working** - Don't break the existing Docker workflow
4. **Test before suggesting** - Run the code locally if possible
5. **Explain changes** - Always explain what you changed and why
6. **Follow existing patterns** - Match the existing code style
7. **Add comments** - Help future developers understand the code
8. **Update docs** - If you change functionality, update relevant docs

## 🔍 Quick Reference

```bash
# Setup
./setup-local.sh           # One-time setup

# Development
make run                   # Run adapter
make test                  # Run tests
make format                # Format code
make lint                  # Check code

# Docker
make docker-up             # Start services
make docker-down           # Stop services
make docker-logs           # View logs

# Dependencies
uv add package             # Add package
uv remove package          # Remove package
uv sync --upgrade          # Update all

# Help
make help                  # Show all commands
uv --help                  # uv help
```

## 📞 Support

- Check documentation in project root
- Read error messages carefully
- Test in isolation (disable other components)
- Use `make help` for available commands
