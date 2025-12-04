# SearXNG Docker Tavily Adapter

**Free Tavily API replacement powered by SearXNG** 🔍

Run SearXNG through a Tavily-compatible API. No limits, no API keys, full privacy.

> 🎯 **Ready-to-run Docker Compose stack** with SearXNG + Tavily-compatible API adapter

## 🚀 Quick Start

### 🐳 Docker (production-ready)

```bash
# 1. Clone the repo
git clone git@github.com:vakovalskii/searxng-docker-tavily-adapter.git
# or HTTPS: git clone https://github.com/vakovalskii/searxng-docker-tavily-adapter.git
cd searxng-docker-tavily-adapter

# 2. Configure the stack
cp config.example.yaml config.yaml
# Update secret_key inside config.yaml

# 3. Start the services
docker compose up -d

# 4. Smoke test
curl -X POST "http://localhost:8001/search" \
     -H "Content-Type: application/json" \
     -d '{"query": "bitcoin price", "max_results": 3}'
```

### 💻 Local development (uv)

```bash
# 1. Clone the repo
git clone https://github.com/vakovalskii/searxng-docker-tavily-adapter.git
cd searxng-docker-tavily-adapter

# 2. Automated setup
./setup-local.sh     # macOS/Linux
# or
.\setup-local.ps1    # Windows

# 3. Start Docker services (SearXNG + Redis)
make docker-up       # Opens the right ports for local work

# 4. Run the adapter locally
make run             # Connects to SearXNG via localhost:8999

# Manual alternative:
# uv sync              # install dependencies
# cp config.local.yaml config.yaml  # local development config
# make docker-up       # start Docker services
# make run             # run the adapter
```

📖 **Detailed guide**: [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md)

**Local development tips:**
- Use `config.local.yaml` as the base for `config.yaml` (preconfigured for localhost:8999)
- `make docker-up` automatically exposes the right ports for the host
- The adapter connects to SearXNG at `http://localhost:8999`

## ☁️ Azure Container Apps Deployment

### Automated deployment with GitHub Actions

The project ships with a ready-to-use GitHub Actions workflow that deploys to Azure Container Apps with Redis and SearXNG sidecars.

#### Prerequisites

1. **Azure Service Principal** with Contributor rights on the target resource group
2. **GitHub Secrets** in your repository:
   - `AZURE_CREDENTIALS` — service principal JSON:
     ```json
     {
       "clientId": "xxx",
       "clientSecret": "xxx",
       "subscriptionId": "xxx",
       "tenantId": "xxx"
     }
     ```
   - `CONFIG_YAML` — contents of `config.azure.yaml` adjusted for your environment
   - `SEARXNG_SECRET_KEY` — random string (32+ characters), e.g. `openssl rand -hex 32`

#### Configure deployment inputs

1. Copy the Azure configuration template:
   ```bash
   cp config.azure.yaml config.production.yaml
   ```

2. Edit `config.production.yaml`:
   ```yaml
   server:
     secret_key: "REPLACE_WITH_RANDOM_32_CHAR_STRING"  # Required
   
   # You can keep the rest as defaults
   # localhost is used by sidecars inside Azure Container Apps
   ```

3. Add the content to GitHub secrets:
   ```bash
   # Repo settings: Settings → Secrets → Actions → New repository secret
   # Name: CONFIG_YAML
   # Value: contents of config.production.yaml
   ```

#### Run the deployment

1. Open **Actions** in your GitHub repository
2. Select **Deploy to Azure Container Apps**
3. Click **Run workflow** → **Run workflow**
4. Wait about 5–10 minutes until the job finishes

#### After deployment

```bash
# Retrieve the public URL
az containerapp show \
  -n je-tavily-adapter \
  -g RG-GBLI-AI-Risk-Insights \
  --query properties.configuration.ingress.fqdn -o tsv

# Health check
curl https://<app-url>/health

# Sample search
curl -X POST https://<app-url>/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"Azure Cloud","max_results":3}'
```

#### Azure deployment diagram

```
┌───────────────────────────────────────────────────────┐
│           Azure Container App Instance                │
│                                                       │
│  ┌──────────────────┐  ┌──────────┐  ┌────────────┐  │
│  │ Tavily Adapter   │  │  Redis   │  │  SearXNG   │  │
│  │ (main container) │  │ (sidecar)│  │ (sidecar)  │  │
│  │ Port: 8001       │  │ :6379    │  │ :8080      │  │
│  └──────────────────┘  └──────────┘  └────────────┘  │
│           ▲                                           │
│           │ All containers share localhost            │
└───────────┼───────────────────────────────────────────┘
            │
            │ Ingress (HTTPS)
            ▼
     Your API client
```

**Highlights:**
- All three containers run in one pod and share localhost networking
- Only port 8001 (Tavily Adapter) is exposed through HTTPS ingress
- Redis and SearXNG stay internal and reachable only via localhost
- Autoscaling keeps 1–3 replicas running
- Storage is ephemeral (Redis data resets on restart)

#### Tuning the workflow

To adjust deployment parameters edit `.github/workflows/azure-deploy.yml`:

```yaml
env:
  RESOURCE_GROUP: RG-GBLI-AI-Risk-Insights    # Your resource group
  CONTAINER_APP_NAME: je-tavily-adapter       # Application name
  CONTAINER_ENV_NAME: je-tavily-env           # Container Apps environment
  LOCATION: westeurope                         # Azure region
```

## 💡 Usage

### Drop-in replacement for Tavily

```python
# Install the official Tavily client
pip install tavily-python

from tavily import TavilyClient

# Just change the base_url
client = TavilyClient(
    api_key="ignored",  # The adapter ignores the key
    base_url="http://localhost:8001"  # Point to your adapter
)

# Interact with the API as usual
response = client.search(
    query="bitcoin price",
    max_results=5,
    include_raw_content=True
)
```

### Simple HTTP API

```python
import requests

response = requests.post("http://localhost:8001/search", json={
    "query": "what is machine learning",
    "max_results": 5,
    "include_raw_content": True
})

results = response.json()
```

## 📦 What is inside

- **SearXNG** (port 8999) — powerful meta search engine
- **Tavily Adapter** (port 8001) — Tavily-compatible HTTP API
- **Redis** — caching backend for SearXNG
- **Unified config** — `config.yaml` shared across services

## 🎯 Benefits

| Tavily (official) | SearXNG Adapter |
|-------------------|-----------------|
| 💰 Paid | ✅ Free |
| 🔑 Requires API key | ✅ No keys |
| 📊 Request limits | ✅ Unlimited |
| 🏢 External SaaS | ✅ Self-hosted |
| ❓ Unknown sources | ✅ You pick engines |

## 📋 API

### Request
```json
{
  "query": "search query",
  "max_results": 10,
  "include_raw_content": false
}
```

### Response
```json
{
  "query": "search query",
  "results": [
    {
      "url": "https://example.com",
      "title": "Title",
      "content": "Short description...",
      "score": 0.9,
      "raw_content": "Full page text..."
    }
  ],
  "response_time": 1.23,
  "request_id": "uuid"
}
```

### Extract API (crawl4ai)

```bash
curl -X POST "http://localhost:8001/extract" \
  -H "Content-Type: application/json" \
  -d '{
        "urls": ["https://www.spacex.com/"],
        "include_images": true,
        "include_favicon": true,
        "extract_depth": "advanced",
        "format": "markdown"
      }'
```

```json
{
  "request_id": "uuid",
  "response_time": 2.31,
  "results": [
    {
      "url": "https://www.spacex.com/",
      "title": "SpaceX",
      "language": "en",
      "raw_content": "# SpaceX ...",
      "images": [
        {"url": "https://...", "description": "Falcon 9", "score": 0.91}
      ],
      "favicon": "https://www.spacex.com/favicon.ico",
      "metadata": {"status_code": 200}
    }
  ],
  "failed_results": []
}
```

> ℹ️ The `/extract` endpoint relies on [crawl4ai](https://github.com/unclecode/crawl4ai).  
> - **Docker**: the `simple_tavily_adapter` image downloads Chromium via Playwright during build.  
> - **Local**: run `pip install -r simple_tavily_adapter/requirements.txt && crawl4ai-setup` to install Playwright browsers.  
> Limits and timeouts live under `adapter.extract` inside `config.yaml`.

## 🕷️ Raw Content scraping

### How `include_raw_content` works

```python
# Without raw_content (fast)
response = client.search(
    query="machine learning",
    max_results=3
)
# content = short snippet from the search engine
# raw_content = null

# With raw_content (slower, more data)
response = client.search(
    query="machine learning", 
    max_results=3,
    include_raw_content=True
)
# content = short snippet from the search engine
# raw_content = full page text (up to 2500 characters)
```

### Under the hood

1. **Search via SearXNG** — collect URLs and snippets
2. **Parallel scraping** — download HTML for each page
3. **Content cleanup** — remove script, style, nav, footer
4. **Text extraction** — convert HTML to plain text
5. **Content trimming** — keep up to 2500 characters optimised for LLM input

### Scraper configuration

Inside `config.yaml`:

```yaml
adapter:
  scraper:
    timeout: 10                    # Per-page timeout in seconds
    max_content_length: 2500       # Maximum raw_content length
    user_agent: "Mozilla/5.0..."   # User-Agent header for requests
```

### Performance

| Mode | Response time | Data volume |
|------|---------------|-------------|
| Without raw_content | ~1–2 s | Snippets only |
| With raw_content | ~3–5 s | Full page text |

> 💡 **Tip**: Set `raw_content=True` when you need full context for LLMs, keep it `False` for fast searches.

## ⚙️ Configuration

Full reference: [CONFIG_SETUP.md](CONFIG_SETUP.md)

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Your code     │───▶│  Tavily Adapter  │───▶│     SearXNG     │
│                 │    │   (port 8001)    │    │   (port 8999)   │
│ requests.post() │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │  Web Scraping    │    │ Google, Bing,   │
                       │  (raw_content)   │    │ DuckDuckGo...   │
                       └──────────────────┘    └─────────────────┘
```

## 🔧 Development

### Local development with uv (recommended)

```bash
# Install uv if you do not have it yet
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies and create the virtual environment
uv sync

# Install Playwright browsers for the /extract endpoint
source .venv/bin/activate
crawl4ai-setup

# Start SearXNG via Docker
docker compose up -d searxng redis

# Run the adapter locally with hot reload
uv run uvicorn simple_tavily_adapter.main:app --reload --port 8001

# Smoke tests
uv run python simple_tavily_adapter/test_client.py
```

📖 **Complete guide**: [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md)

### Traditional workflow (pip)

```bash
# Local adapter development
cd simple_tavily_adapter
pip install -r requirements.txt
crawl4ai-setup  # Install Playwright browsers once
python main.py

# Tests
python test_client.py
```

## 📚 Documentation

### Local development
- **[LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md)** — full uv-based development guide
- **[UV_CHEATSHEET.md](UV_CHEATSHEET.md)** — uv command quick reference
- **[UV_MIGRATION_NOTES.md](UV_MIGRATION_NOTES.md)** — migration FAQs
- **[NETWORKING_GUIDE.md](NETWORKING_GUIDE.md)** — networking setup for local work

### Configuration and deployment
- **[CONFIG_SETUP.md](CONFIG_SETUP.md)** — configuration guide
- **[AZURE_DEPLOYMENT.md](AZURE_DEPLOYMENT.md)** — Azure deployment walkthrough

### Testing
- **[TESTING_RAW_CONTENT.md](TESTING_RAW_CONTENT.md)** — raw content scraping tests

## 📜 License

MIT License — do whatever you like. 🎉
