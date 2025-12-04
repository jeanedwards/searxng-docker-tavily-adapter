# Local Development Guide

This guide covers local development setup using `uv`, the modern Python package manager.

## Why uv?

- **⚡ Fast**: 10-100x faster than pip
- **🔒 Reliable**: Deterministic dependency resolution
- **🎯 Simple**: One tool for all Python package management
- **🔄 Compatible**: Works seamlessly with existing requirements.txt and pyproject.toml

## Prerequisites

### Install uv

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**
```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Alternative (via pip):**
```bash
pip install uv
```

## Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/vakovalskii/searxng-docker-tavily-adapter.git
cd searxng-docker-tavily-adapter
```

### 2. Setup Configuration
```bash
# Copy local development config (optimized for running outside Docker)
cp config.local.yaml config.yaml

# Edit config.yaml to set your secret_key
# IMPORTANT: Make sure searxng_url is set to http://localhost:8999
nano config.yaml
```

**Key Configuration for Local Development:**
- `adapter.searxng_url: "http://localhost:8999"` ✅ (correct for local)
- NOT `"http://searxng:8080"` ❌ (only for Docker internal network)

### 3. Install Dependencies with uv
```bash
# Create virtual environment and install dependencies
# This will automatically create .venv/ and install all packages
uv sync
```

### 4. Install Playwright Browsers (for crawl4ai)
```bash
# Activate the virtual environment
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate     # Windows

# Install Playwright browsers (needed for /extract endpoint)
crawl4ai-setup
```

### 5. Start SearXNG (Docker)
The adapter needs SearXNG running. Start it with the local development compose setup:
```bash
# Start SearXNG and Redis with ports exposed for local access
make docker-up

# This is equivalent to:
# docker compose -f docker-compose.yaml -f docker-compose.local.yaml up -d searxng redis

# Services will be available at:
# - SearXNG: http://localhost:8999
# - Redis: localhost:6379 (exposed for future use)
```

### 6. Run the Adapter Locally
```bash
# With virtual environment activated
python -m simple_tavily_adapter.main

# Or using uvicorn directly for auto-reload
uvicorn simple_tavily_adapter.main:app --reload --host 0.0.0.0 --port 8001
```

### 7. Test the API
```bash
# In another terminal
curl -X POST "http://localhost:8001/search" \
     -H "Content-Type: application/json" \
     -d '{"query": "test search", "max_results": 3}'
```

## Development Workflow

### Install Development Dependencies
```bash
# Install with dev dependencies (pytest, ruff, etc.)
uv sync --group dev
```

### Code Formatting and Linting
```bash
# Format code with ruff
uv run ruff format .

# Check for linting issues
uv run ruff check .

# Fix auto-fixable issues
uv run ruff check --fix .
```

### Running Tests
```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_services.py

# Run with verbose output
uv run pytest -v
```

### Adding New Dependencies

**Add runtime dependency:**
```bash
# Add a new package
uv add package-name

# Add with version constraint
uv add "package-name>=1.0.0"
```

**Add development dependency:**
```bash
# Add to dev group
uv add --group dev pytest-cov
```

**Remove dependency:**
```bash
uv remove package-name
```

### Updating Dependencies
```bash
# Update all dependencies
uv sync --upgrade

# Update specific package
uv add package-name --upgrade
```

## Project Structure

```
searxng-docker-tavily-adapter/
├── pyproject.toml              # Project metadata and dependencies (uv-managed)
├── .python-version             # Python version specification
├── .venv/                      # Virtual environment (auto-created by uv)
├── config.yaml                 # Runtime configuration
├── simple_tavily_adapter/      # Main application code
│   ├── main.py                 # FastAPI app entry point
│   ├── routes.py               # API route handlers
│   ├── services.py             # Business logic
│   ├── models.py               # Pydantic models
│   ├── config_loader.py        # Config management
│   ├── utils.py                # Utility functions
│   └── requirements.txt        # Kept for Docker compatibility
└── tests/                      # Test suite (create as needed)
```

## Common Tasks

### Run Adapter with Auto-Reload
```bash
# Automatically reloads when code changes
uv run uvicorn simple_tavily_adapter.main:app --reload --port 8001
```

### Check Configuration
```bash
# Verify config loads correctly
uv run python -c "from simple_tavily_adapter.config_loader import config; print(config)"
```

### Run Test Client
```bash
uv run python simple_tavily_adapter/test_client.py
```

### View Dependency Tree
```bash
# Show what's installed
uv pip list

# Show dependency tree
uv pip tree
```

## Networking Setup

### Understanding the Setup

When developing locally:
- **Adapter**: Runs on your machine (not in Docker)
- **SearXNG**: Runs in Docker, exposed on port 8999
- **Redis**: Runs in Docker, used by SearXNG

The adapter connects to SearXNG via `http://localhost:8999`.

### Configuration Files

- **`config.local.yaml`**: Template for local development (uses localhost:8999)
- **`config.example.yaml`**: Template for Docker deployment (uses searxng:8080)
- **`config.yaml`**: Your actual config (git-ignored)

### Docker Compose Files

- **`docker-compose.yaml`**: Base configuration
- **`docker-compose.local.yaml`**: Overrides for local development (exposes ports)

When running `make docker-up`, both files are used automatically.

## Troubleshooting

### Connection Refused Error

If you see "Connection refused" when the adapter tries to reach SearXNG:
```bash
# Check SearXNG is running
docker compose ps

# Verify SearXNG is accessible
curl http://localhost:8999/search?q=test&format=json

# Check your config.yaml has the correct URL
grep searxng_url config.yaml
# Should show: searxng_url: "http://localhost:8999"
```

### Wrong SearXNG URL in Config

If your config has `http://searxng:8080` (Docker internal URL):
```bash
# Update it to localhost for local development
sed -i 's|http://searxng:8080|http://localhost:8999|g' config.yaml
```

### Virtual Environment Not Activated
```bash
# Manually activate
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
```

### SearXNG Connection Error
Ensure SearXNG is running:
```bash
docker compose ps
curl http://localhost:8999/search?q=test&format=json
```

### Playwright/Crawl4AI Issues
Reinstall browsers:
```bash
source .venv/bin/activate
playwright install chromium
# or
crawl4ai-setup
```

### Port Already in Use
Change port in config.yaml or use different port:
```bash
uv run uvicorn simple_tavily_adapter.main:app --port 8001
```

## Using with Docker Compose

The project still supports Docker Compose for full-stack deployment:

```bash
# Full stack (SearXNG + Redis + Adapter in Docker)
docker compose up -d

# View logs
docker compose logs -f adapter

# Stop all services
docker compose down
```

## Tips for Efficient Development

1. **Use `uv run` prefix**: No need to activate virtual environment for one-off commands
   ```bash
   uv run python simple_tavily_adapter/test_client.py
   ```

2. **Fast dependency changes**: `uv` is much faster than pip for installs
   ```bash
   uv add requests  # Installs in seconds
   ```

3. **Lock file benefits**: `uv.lock` ensures reproducible builds across machines

4. **Parallel execution**: uv downloads and installs packages in parallel

## Comparison: uv vs Traditional Setup

| Task | Traditional (pip) | Modern (uv) |
|------|------------------|-------------|
| Create venv | `python -m venv .venv` | `uv sync` (automatic) |
| Activate venv | `source .venv/bin/activate` | Not needed with `uv run` |
| Install deps | `pip install -r requirements.txt` | `uv sync` |
| Add package | Edit requirements.txt + `pip install` | `uv add package-name` |
| Update | `pip install --upgrade` | `uv sync --upgrade` |
| Speed | ⚪ Slow | ⚡ 10-100x faster |

## Quick Command Reference

See [UV_CHEATSHEET.md](UV_CHEATSHEET.md) for a comprehensive quick reference.

```bash
# Most used commands
uv sync                    # Install dependencies
uv run python script.py    # Run without activating venv
uv add package             # Add dependency
make run                   # Run adapter with hot-reload
make test                  # Run tests
```

## Further Reading

- [uv Quick Reference](UV_CHEATSHEET.md)
- [uv Documentation](https://docs.astral.sh/uv/)
- [Project Configuration Guide](CONFIG_SETUP.md)
- [Azure Deployment Guide](AZURE_DEPLOYMENT.md)

