# Local development setup script for SearXNG Tavily Adapter (Windows)
# This script automates the setup process for local development using uv

$ErrorActionPreference = "Stop"

Write-Host "🚀 Setting up SearXNG Tavily Adapter for local development..." -ForegroundColor Cyan
Write-Host ""

# Function to print colored messages
function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Write-Warning-Custom {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor Yellow
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

# Check if uv is installed
$uvInstalled = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uvInstalled) {
    Write-Warning-Custom "uv is not installed. Installing uv..."
    try {
        powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
        
        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        
        $uvInstalled = Get-Command uv -ErrorAction SilentlyContinue
        if ($uvInstalled) {
            Write-Success "uv installed successfully"
        } else {
            Write-Error-Custom "Failed to install uv. Please install manually: https://docs.astral.sh/uv/getting-started/installation/"
            exit 1
        }
    } catch {
        Write-Error-Custom "Failed to install uv: $_"
        exit 1
    }
} else {
    $uvVersion = uv --version
    Write-Success "uv is already installed ($uvVersion)"
}

# Check if config.yaml exists
if (-not (Test-Path "config.yaml")) {
    Write-Warning-Custom "config.yaml not found. Creating from config.local.yaml..."
    Copy-Item "config.local.yaml" "config.yaml"
    Write-Success "config.yaml created (optimized for local development)"
    Write-Warning-Custom "IMPORTANT: Edit config.yaml and set your secret_key before running!"
    Write-Warning-Custom "The config is set to use http://localhost:8999 for SearXNG (correct for local dev)"
} else {
    Write-Success "config.yaml exists"
    
    # Check if config has correct searxng_url for local development
    $configContent = Get-Content "config.yaml" -Raw
    if ($configContent -match "searxng_url.*localhost:8999") {
        Write-Success "config.yaml is configured for local development"
    } elseif ($configContent -match "searxng_url.*searxng:8080") {
        Write-Warning-Custom "config.yaml uses Docker internal URL (http://searxng:8080)"
        Write-Warning-Custom "For local development, it should use: http://localhost:8999"
        Write-Warning-Custom "Please update adapter.searxng_url in config.yaml"
    }
}

# Sync dependencies and create virtual environment
Write-Host ""
Write-Host "📦 Installing dependencies with uv..." -ForegroundColor Cyan
uv sync

if ($LASTEXITCODE -eq 0) {
    Write-Success "Dependencies installed"
} else {
    Write-Error-Custom "Failed to install dependencies"
    exit 1
}

# Ask about dev dependencies
Write-Host ""
$installDev = Read-Host "Do you want to install development dependencies (pytest, ruff, etc.)? [y/N]"
if ($installDev -match "^[Yy]") {
    Write-Host "📦 Installing development dependencies..." -ForegroundColor Cyan
    uv sync --group dev
    Write-Success "Development dependencies installed"
}

# Ask about Playwright browsers
Write-Host ""
$installPlaywright = Read-Host "Do you want to install Playwright browsers (needed for /extract endpoint)? [y/N]"
if ($installPlaywright -match "^[Yy]") {
    Write-Host "🌐 Installing Playwright browsers..." -ForegroundColor Cyan
    & .\.venv\Scripts\Activate.ps1
    crawl4ai-setup
    Write-Success "Playwright browsers installed"
    deactivate
}

# Check Docker
Write-Host ""
$dockerInstalled = Get-Command docker -ErrorAction SilentlyContinue
if ($dockerInstalled) {
    Write-Success "Docker is installed"
    
    # Check if docker compose is available
    $composeAvailable = docker compose version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Docker Compose is available"
        
        $startDocker = Read-Host "Do you want to start SearXNG and Redis containers now? [y/N]"
        if ($startDocker -match "^[Yy]") {
            Write-Host "🐳 Starting SearXNG and Redis..." -ForegroundColor Cyan
            docker compose up -d searxng redis
            Write-Success "SearXNG and Redis started"
            
            # Wait for services to start
            Write-Host "Waiting for services to be ready..."
            Start-Sleep -Seconds 5
            
            # Check if SearXNG is responding
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:8999/search?q=test&format=json" -UseBasicParsing -TimeoutSec 5
                if ($response.StatusCode -eq 200) {
                    Write-Success "SearXNG is responding"
                }
            } catch {
                Write-Warning-Custom "SearXNG might not be ready yet. Give it a few more seconds."
            }
        }
    } else {
        Write-Warning-Custom "Docker Compose not found. Install it from: https://docs.docker.com/compose/install/"
    }
} else {
    Write-Warning-Custom "Docker not found. You'll need Docker to run SearXNG."
    Write-Host "Install from: https://docs.docker.com/get-docker/"
}

# Print next steps
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Success "Setup complete! 🎉"
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host ""
Write-Host "1. Edit config.yaml if you haven't already:" -ForegroundColor White
Write-Host "   " -NoNewline; Write-Host "notepad config.yaml" -ForegroundColor Yellow
Write-Host ""
Write-Host "2. Start SearXNG if not running:" -ForegroundColor White
Write-Host "   " -NoNewline; Write-Host "docker compose up -d searxng redis" -ForegroundColor Yellow
Write-Host ""
Write-Host "3. Run the adapter locally:" -ForegroundColor White
Write-Host "   " -NoNewline; Write-Host "uv run uvicorn simple_tavily_adapter.main:app --reload --port 8000" -ForegroundColor Yellow
Write-Host ""
Write-Host "4. Test the API:" -ForegroundColor White
Write-Host "   " -NoNewline; Write-Host "curl -X POST http://localhost:8000/search -H 'Content-Type: application/json' -d '{`"query`":`"test`",`"max_results`":3}'" -ForegroundColor Yellow
Write-Host ""
Write-Host "📖 For more details, see: LOCAL_DEVELOPMENT.md" -ForegroundColor Cyan
Write-Host ""

