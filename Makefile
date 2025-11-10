.PHONY: help install install-dev setup run test lint format clean docker-up docker-down docker-status docker-logs

# Default target - show help
help:
	@echo "🚀 SearXNG Tavily Adapter - Development Commands"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make setup              - Run automated setup script (recommended)"
	@echo "  make install            - Install Python dependencies only"
	@echo "  make install-dev        - Install dev dependencies + Playwright browsers"
	@echo ""
	@echo "Running:"
	@echo "  make run                - Run adapter (auto-starts Docker if needed)"
	@echo "  make docker-up          - Start SearXNG and Redis containers"
	@echo "  make docker-down        - Stop all containers"
	@echo "  make docker-status      - Check if Docker services are running"
	@echo "  make docker-logs        - View Docker logs"
	@echo ""
	@echo "Development:"
	@echo "  make test               - Run tests with pytest"
	@echo "  make lint               - Check code with ruff"
	@echo "  make format             - Format code with ruff"
	@echo "  make clean              - Remove cache and temp files"
	@echo ""
	@echo "Utilities:"
	@echo "  make test-api           - Test search endpoint"
	@echo "  make health             - Check health endpoint"
	@echo "  make list               - List installed packages"
	@echo "  make tree               - Show dependency tree"
	@echo "  make update             - Update all dependencies"
	@echo "  make requirements       - Generate requirements.txt for Docker"
	@echo ""
	@echo "Note: Playwright browsers (for /extract) are auto-installed with install-dev"
	@echo "      requirements.txt is auto-generated in CI/CD from pyproject.toml"
	@echo ""

# Run automated setup script
setup:
	@chmod +x setup-local.sh
	@./setup-local.sh

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	uv sync

# Install with development dependencies
install-dev:
	@echo "📦 Installing dependencies (including dev)..."
	uv sync --group dev
	@echo ""
	@echo "🌐 Installing Playwright browsers (needed for /extract endpoint)..."
	@bash -c "source .venv/bin/activate && playwright install chromium" || echo "⚠️  Playwright install failed, you can run 'make install-playwright' later"
	@echo "✓ Development environment ready!"

# Run the adapter locally with auto-reload
# Automatically starts Docker dependencies if not running
run:
	@echo "🚀 Starting adapter with auto-reload..."
	@echo ""
	@echo "🔍 Checking if Docker dependencies are running..."
	@if ! docker compose ps --services --filter "status=running" | grep -q searxng; then \
		echo "⚠️  SearXNG not running, starting Docker services..."; \
		echo ""; \
		$(MAKE) docker-up; \
		echo ""; \
		echo "⏳ Waiting 5 seconds for services to initialize..."; \
		sleep 5; \
	else \
		echo "✓ Docker services are running"; \
	fi
	@echo ""
	@echo "🚀 Starting adapter..."
	@echo "ℹ️  Adapter will use SearXNG at http://localhost:8999"
	@echo "ℹ️  Press Ctrl+C to stop"
	@echo ""
	uv run uvicorn simple_tavily_adapter.main:app --reload --host 0.0.0.0 --port 8000

# Start Docker containers (SearXNG + Redis) for local development
# Uses docker-compose.local.yaml to expose ports correctly
docker-up:
	@echo "🐳 Starting SearXNG and Redis for local development..."
	@echo "ℹ️  These services will be accessible at:"
	@echo "   - SearXNG: http://localhost:8999"
	@echo "   - Redis: localhost:6379"
	docker compose -f docker-compose.yaml -f docker-compose.local.yaml up -d searxng redis

# Start all Docker containers (including adapter)
docker-up-all:
	@echo "🐳 Starting all containers..."
	docker compose up -d

# Stop Docker containers
docker-down:
	@echo "🛑 Stopping containers..."
	docker compose -f docker-compose.yaml -f docker-compose.local.yaml down

# Check Docker services status
docker-status:
	@echo "📊 Docker Services Status:"
	@echo ""
	@docker compose ps || echo "⚠️  No services found"
	@echo ""
	@if docker compose ps --services --filter "status=running" | grep -q searxng; then \
		echo "✓ SearXNG is running"; \
		echo "  Access at: http://localhost:8999"; \
	else \
		echo "✗ SearXNG is not running"; \
	fi
	@if docker compose ps --services --filter "status=running" | grep -q redis; then \
		echo "✓ Redis is running"; \
	else \
		echo "✗ Redis is not running"; \
	fi

# View adapter logs
docker-logs:
	@echo "📋 Viewing adapter logs..."
	docker compose logs -f adapter

# Run tests
test:
	@echo "🧪 Running tests..."
	uv run pytest -v

# Lint code
lint:
	@echo "🔍 Checking code with ruff..."
	uv run ruff check .

# Format code
format:
	@echo "✨ Formatting code with ruff..."
	uv run ruff format .
	uv run ruff check --fix .

# Clean up cache and temp files
clean:
	@echo "🧹 Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type f -name "*.log" -delete 2>/dev/null || true
	@echo "✓ Cleanup complete"

# Test the API
test-api:
	@echo "🧪 Testing API..."
	@curl -X POST "http://localhost:8000/search" \
	     -H "Content-Type: application/json" \
	     -d '{"query": "test search", "max_results": 3}' \
	     | uv run python -m json.tool

# Check health endpoint
health:
	@echo "🏥 Checking health..."
	@curl -s http://localhost:8000/health | uv run python -m json.tool

# Install Playwright browsers (if needed separately)
install-playwright:
	@echo "🌐 Installing Playwright browsers..."
	@bash -c "source .venv/bin/activate && playwright install chromium"

# Show installed packages
list:
	@echo "📦 Installed packages:"
	@uv pip list

# Show dependency tree
tree:
	@echo "🌳 Dependency tree:"
	@uv pip tree

# Update all dependencies
update:
	@echo "⬆️  Updating dependencies..."
	@uv sync --upgrade

# Create config.yaml from example
config:
	@if [ ! -f config.yaml ]; then \
		echo "📝 Creating config.yaml from example..."; \
		cp config.example.yaml config.yaml; \
		echo "✓ config.yaml created. Please edit it before running."; \
	else \
		echo "⚠️  config.yaml already exists"; \
	fi

# Generate requirements.txt from pyproject.toml (for Docker builds)
requirements:
	@echo "📦 Generating requirements.txt from pyproject.toml..."
	@uv pip compile pyproject.toml -o simple_tavily_adapter/requirements.txt
	@echo "✓ requirements.txt generated at: simple_tavily_adapter/requirements.txt"
	@echo ""
	@echo "Contents:"
	@head -20 simple_tavily_adapter/requirements.txt

