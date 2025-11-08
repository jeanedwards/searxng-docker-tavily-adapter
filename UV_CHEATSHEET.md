# uv Quick Reference Guide

A quick reference for using `uv` with this project.

## Installation

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Alternative (via pip)
pip install uv
```

## Project Setup

```bash
# Create virtual environment and install all dependencies
uv sync

# Install with development dependencies
uv sync --group dev

# Update all dependencies
uv sync --upgrade
```

## Running Commands

```bash
# Run command in virtual environment (no need to activate!)
uv run python script.py
uv run pytest
uv run uvicorn simple_tavily_adapter.main:app

# Run with arguments
uv run python -m simple_tavily_adapter.main
```

## Managing Dependencies

### Add Dependencies

```bash
# Add runtime dependency
uv add fastapi

# Add with version constraint
uv add "fastapi>=0.100.0"

# Add development dependency
uv add --group dev pytest

# Add multiple packages
uv add fastapi uvicorn aiohttp
```

### Remove Dependencies

```bash
# Remove package
uv remove package-name

# Remove dev dependency
uv remove --group dev pytest
```

### Update Dependencies

```bash
# Update all packages
uv sync --upgrade

# Update specific package
uv add package-name --upgrade
```

## Package Information

```bash
# List installed packages
uv pip list

# Show dependency tree
uv pip tree

# Show package info
uv pip show package-name

# Search for packages
uv pip search pattern
```

## Virtual Environment

```bash
# uv automatically creates .venv/ when running uv sync

# Manually create venv
uv venv

# Create with specific Python version
uv venv --python 3.11

# Activate manually (usually not needed with uv run)
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows

# Deactivate
deactivate
```

## Working with This Project

### First Time Setup

```bash
# Clone and setup
git clone https://github.com/vakovalskii/searxng-docker-tavily-adapter.git
cd searxng-docker-tavily-adapter

# Run automated setup
./setup-local.sh  # macOS/Linux
.\setup-local.ps1 # Windows

# Or manual setup
uv sync
cp config.example.yaml config.yaml
# Edit config.yaml
```

### Daily Development

```bash
# Start Docker dependencies
docker compose up -d searxng redis

# Run adapter with hot-reload
uv run uvicorn simple_tavily_adapter.main:app --reload

# Run tests
uv run pytest

# Format code
uv run ruff format .

# Check linting
uv run ruff check .
```

### Using Makefile (convenience)

```bash
make help         # Show all commands
make install      # Install dependencies
make run          # Run adapter
make test         # Run tests
make format       # Format code
make lint         # Check code
make docker-up    # Start Docker services
```

## Comparison with Other Tools

| Task | pip | poetry | uv |
|------|-----|--------|-----|
| Install deps | `pip install -r requirements.txt` | `poetry install` | `uv sync` |
| Add package | Edit requirements.txt + install | `poetry add pkg` | `uv add pkg` |
| Run script | `python script.py` | `poetry run python script.py` | `uv run python script.py` |
| Update deps | `pip install --upgrade` | `poetry update` | `uv sync --upgrade` |
| Lock file | Manual or pip-tools | poetry.lock | uv.lock |
| Speed | ⚪ Slow | 🟡 Medium | ⚡ Fast (10-100x) |

## Tips & Tricks

### Speed Tips

```bash
# uv caches packages globally - subsequent installs are instant!
# Clear cache if needed:
uv cache clean

# Show cache info
uv cache info
```

### No Activation Needed

```bash
# Instead of:
source .venv/bin/activate
python script.py

# Just use:
uv run python script.py
```

### Lock File Benefits

```bash
# uv.lock ensures everyone gets the same versions
# Commit it to git for reproducible builds
git add uv.lock
git commit -m "feat: add uv lock file"
```

### Python Version Management

```bash
# Use specific Python version
uv venv --python 3.11

# Or set in .python-version file
echo "3.11" > .python-version
```

### Scripting with uv

```bash
# Use in CI/CD pipelines
uv sync
uv run pytest

# Use in scripts
#!/bin/bash
set -e
uv sync
uv run python main.py
```

## Troubleshooting

### uv not found after install

```bash
# Reload shell or add to PATH
source ~/.bashrc  # Linux
source ~/.zshrc   # macOS with zsh

# Or use full path
~/.cargo/bin/uv sync
```

### Virtual environment issues

```bash
# Remove and recreate
rm -rf .venv
uv sync
```

### Dependency conflicts

```bash
# Check what's conflicting
uv pip tree

# Try upgrading packages
uv sync --upgrade
```

### Package not found

```bash
# Make sure you're in project directory
cd /path/to/searxng-docker-tavily-adapter

# Verify pyproject.toml exists
ls pyproject.toml
```

## Configuration Files

This project uses these uv-related files:

- **`pyproject.toml`** - Project metadata and dependencies
- **`uv.lock`** - Locked dependency versions (auto-generated)
- **`.python-version`** - Python version specification
- **`.venv/`** - Virtual environment (auto-created)

## Further Reading

- [uv Documentation](https://docs.astral.sh/uv/)
- [uv GitHub Repository](https://github.com/astral-sh/uv)
- [Project Guide](LOCAL_DEVELOPMENT.md)
- [Configuration Setup](CONFIG_SETUP.md)

## Quick Command Reference

```bash
# Most common commands
uv sync                    # Install/update dependencies
uv add package             # Add new package
uv remove package          # Remove package
uv run command             # Run command in venv
uv pip list                # List installed packages
uv sync --upgrade          # Update all packages
uv cache clean             # Clear cache

# This project specific
make setup                 # One-time setup
make run                   # Run adapter
make test                  # Run tests
make format                # Format code
```

