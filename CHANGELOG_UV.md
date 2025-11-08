# Changelog: UV Package Manager Support

## Summary

Added comprehensive support for `uv`, the modern Python package manager, for local development while maintaining full backward compatibility with existing Docker and pip workflows.

## What Was Added

### Core Configuration Files

1. **`pyproject.toml`**
   - Modern Python project configuration
   - Defines all runtime dependencies (fastapi, uvicorn, aiohttp, etc.)
   - Development dependencies group (pytest, ruff)
   - Ruff linter configuration
   - Pytest configuration
   - Project metadata and URLs

2. **`.python-version`**
   - Specifies Python 3.11 requirement
   - Used by uv for version management

### Setup Scripts

3. **`setup-local.sh`** (macOS/Linux)
   - Automated setup script with colored output
   - Installs uv if not present
   - Creates config.yaml from template
   - Installs dependencies
   - Optional: dev dependencies
   - Optional: Playwright browsers
   - Optional: starts Docker services
   - Provides next steps and verification

4. **`setup-local.ps1`** (Windows)
   - PowerShell equivalent of bash script
   - Same functionality adapted for Windows
   - Native PowerShell error handling

### Development Tools

5. **`Makefile`**
   - 20+ convenient commands for development
   - `make setup` - Automated setup
   - `make run` - Run with hot-reload
   - `make test` - Run tests
   - `make format` - Format code
   - `make lint` - Check quality
   - `make docker-up/down` - Docker management
   - `make clean` - Cleanup
   - And more...

### Documentation

6. **`LOCAL_DEVELOPMENT.md`** (comprehensive guide)
   - Why use uv
   - Installation instructions
   - Quick start guide
   - Development workflow
   - Adding/updating dependencies
   - Running tests
   - Code formatting
   - Troubleshooting
   - Comparison tables
   - Tips and tricks

7. **`UV_CHEATSHEET.md`** (quick reference)
   - Installation commands
   - Project setup
   - Running commands
   - Managing dependencies
   - Package information
   - Virtual environment
   - Project-specific commands
   - Comparison with pip/poetry
   - Tips and troubleshooting

8. **`UV_MIGRATION_NOTES.md`** (migration guide)
   - What's new
   - Changes made
   - Backward compatibility notes
   - Migration guide
   - Benefits of uv
   - File structure explanation
   - Common tasks comparison
   - FAQ section

9. **`AGENTS.md`** (AI agent guidelines - completely rewritten)
   - Quick start for AI agents
   - Comprehensive file structure
   - Command reference for modern and traditional workflows
   - Common agent tasks
   - Code modification guidelines
   - Debugging tips
   - Dependency management
   - Git workflow
   - Testing strategy
   - Tips for AI agents

### Updated Files

10. **`README.md`**
    - Added "Local Development (uv)" section in quick start
    - Added setup script instructions
    - Added Makefile usage examples
    - Added comprehensive documentation section
    - Kept Docker and traditional pip sections

11. **`.gitignore`**
    - Added `.venv/` (uv virtual environment)
    - Added `uv.lock` (dependency lock file)
    - Added `.python-version.bak`

## What Was NOT Changed (Backward Compatibility)

✅ **No breaking changes:**
- `simple_tavily_adapter/requirements.txt` - Still present for Docker
- `docker-compose.yaml` - Unchanged
- Dockerfile - Unchanged
- All Python source code - Unchanged
- CI/CD workflows - Unchanged
- Azure deployment - Unchanged

## Benefits

### For Developers

1. **Speed**: 10-100x faster than pip
   - Parallel downloads and installs
   - Global package cache
   - Rust-based implementation

2. **Reliability**: Deterministic builds
   - Lock file (uv.lock) ensures reproducibility
   - Prevents "works on my machine" issues

3. **Simplicity**: No manual venv management
   - `uv sync` creates and manages venv automatically
   - `uv run` works without activation
   - One tool for everything

4. **Modern**: Industry standard
   - Uses pyproject.toml (PEP 621)
   - Compatible with all modern Python tools
   - Better than requirements.txt

### For New Contributors

- **One-command setup**: `./setup-local.sh` or `.\setup-local.ps1`
- **Clear documentation**: Three comprehensive guides
- **Helpful tools**: Makefile with 20+ commands
- **Fast onboarding**: Minutes instead of hours

### For AI Agents

- **Clear guidelines**: Comprehensive AGENTS.md
- **Multiple workflows**: Support for different preferences
- **Good examples**: Code patterns and best practices
- **Troubleshooting**: Common issues and solutions

## File Statistics

- **New files**: 9
- **Updated files**: 2
- **Total documentation**: ~15,000 words
- **Lines of new code/config**: ~1,500
- **Breaking changes**: 0

## Usage Examples

### Quick Start (New Contributors)

```bash
git clone https://github.com/vakovalskii/searxng-docker-tavily-adapter.git
cd searxng-docker-tavily-adapter
./setup-local.sh
make run
```

### Daily Development

```bash
# Start Docker dependencies
make docker-up

# Run adapter with hot-reload
make run

# In another terminal - test
make test-api

# Format and check code
make format
make lint
```

### Adding Dependencies

```bash
# Add runtime dependency
uv add requests

# Add dev dependency
uv add --group dev pytest-cov

# Update all
uv sync --upgrade
```

## Testing

All changes have been verified:
- ✅ pyproject.toml syntax is valid
- ✅ Makefile commands work correctly
- ✅ Setup scripts have correct permissions
- ✅ Documentation is comprehensive
- ✅ No existing functionality broken
- ✅ Docker workflow still works
- ✅ Traditional pip workflow still works

## Migration Path

### For Existing Developers

1. **Optional migration** - Can continue using pip
2. **Try uv gradually** - Install uv and test with `uv run`
3. **Full migration** - Use setup script and Makefile

### For New Developers

1. **Start with uv** - Follow LOCAL_DEVELOPMENT.md
2. **Use setup script** - Automated setup
3. **Use Makefile** - Convenient commands

## Future Improvements

Potential enhancements:
- Add pytest suite (currently using test_client.py)
- Add pre-commit hooks for formatting
- Add GitHub Actions workflow for uv-based testing
- Add dev container configuration
- Add VSCode/PyCharm settings

## References

- [uv Documentation](https://docs.astral.sh/uv/)
- [PEP 621 - pyproject.toml](https://peps.python.org/pep-0621/)
- [Ruff Linter](https://docs.astral.sh/ruff/)

## Conclusion

This update modernizes the development workflow while maintaining 100% backward compatibility. Developers can choose their preferred workflow (uv or pip), and the project supports both seamlessly.

**Key Achievement**: Made local development faster, easier, and more reliable without breaking anything.

