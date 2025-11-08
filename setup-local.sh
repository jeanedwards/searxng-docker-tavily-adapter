#!/bin/bash

# Local development setup script for SearXNG Tavily Adapter
# This script automates the setup process for local development using uv

set -e  # Exit on error

echo "🚀 Setting up SearXNG Tavily Adapter for local development..."
echo ""

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored messages
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    print_warning "uv is not installed. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Source the uv installation
    if [ -f "$HOME/.cargo/env" ]; then
        source "$HOME/.cargo/env"
    fi
    
    if command -v uv &> /dev/null; then
        print_success "uv installed successfully"
    else
        print_error "Failed to install uv. Please install manually: https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    fi
else
    print_success "uv is already installed ($(uv --version))"
fi

# Check if config.yaml exists
if [ ! -f "config.yaml" ]; then
    print_warning "config.yaml not found. Creating from config.local.yaml..."
    cp config.local.yaml config.yaml
    print_success "config.yaml created (optimized for local development)"
    print_warning "IMPORTANT: Edit config.yaml and set your secret_key before running!"
    print_warning "The config is set to use http://localhost:8999 for SearXNG (correct for local dev)"
else
    print_success "config.yaml exists"
    
    # Check if config has correct searxng_url for local development
    if grep -q "searxng_url.*localhost:8999" config.yaml 2>/dev/null; then
        print_success "config.yaml is configured for local development"
    elif grep -q "searxng_url.*searxng:8080" config.yaml 2>/dev/null; then
        print_warning "config.yaml uses Docker internal URL (http://searxng:8080)"
        print_warning "For local development, it should use: http://localhost:8999"
        print_warning "Please update adapter.searxng_url in config.yaml"
    fi
fi

# Sync dependencies and create virtual environment
echo ""
echo "📦 Installing dependencies with uv..."
uv sync

print_success "Dependencies installed"

# Check if we should install dev dependencies
read -p "Do you want to install development dependencies (pytest, ruff, etc.)? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📦 Installing development dependencies..."
    uv sync --group dev
    print_success "Development dependencies installed"
fi

# Install Playwright browsers
echo ""
read -p "Do you want to install Playwright browsers (needed for /extract endpoint)? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🌐 Installing Playwright browsers..."
    source .venv/bin/activate
    crawl4ai-setup
    print_success "Playwright browsers installed"
    deactivate 2>/dev/null || true
fi

# Check Docker
echo ""
if command -v docker &> /dev/null; then
    print_success "Docker is installed"
    
    # Check if docker compose is available
    if docker compose version &> /dev/null; then
        print_success "Docker Compose is available"
        
        read -p "Do you want to start SearXNG and Redis containers now? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "🐳 Starting SearXNG and Redis..."
            docker compose up -d searxng redis
            print_success "SearXNG and Redis started"
            
            # Wait a bit for services to start
            echo "Waiting for services to be ready..."
            sleep 5
            
            # Check if SearXNG is responding
            if curl -s -o /dev/null -w "%{http_code}" http://localhost:8999/search?q=test&format=json | grep -q "200"; then
                print_success "SearXNG is responding"
            else
                print_warning "SearXNG might not be ready yet. Give it a few more seconds."
            fi
        fi
    else
        print_warning "Docker Compose not found. Install it from: https://docs.docker.com/compose/install/"
    fi
else
    print_warning "Docker not found. You'll need Docker to run SearXNG."
    echo "Install from: https://docs.docker.com/get-docker/"
fi

# Print next steps
echo ""
echo "═══════════════════════════════════════════════════════════"
print_success "Setup complete! 🎉"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo ""
echo "1. Edit config.yaml if you haven't already:"
echo "   ${YELLOW}nano config.yaml${NC}"
echo ""
echo "2. Start SearXNG if not running:"
echo "   ${YELLOW}docker compose up -d searxng redis${NC}"
echo ""
echo "3. Run the adapter locally:"
echo "   ${YELLOW}uv run uvicorn simple_tavily_adapter.main:app --reload --port 8000${NC}"
echo ""
echo "4. Test the API:"
echo "   ${YELLOW}curl -X POST http://localhost:8000/search -H 'Content-Type: application/json' -d '{\"query\":\"test\",\"max_results\":3}'${NC}"
echo ""
echo "📖 For more details, see: LOCAL_DEVELOPMENT.md"
echo ""

