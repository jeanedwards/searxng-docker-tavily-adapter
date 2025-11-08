# SearXNG Tavily Adapter

**Tavily-compatible wrapper for SearXNG** — use SearXNG with the same API Tavily provides!

## 🚀 Quick setup

1. **Copy the example configuration:**
   ```bash
   cp config.example.yaml config.yaml
   ```

2. **Edit config.yaml:**
   ```bash
   nano config.yaml
   # or
   code config.yaml
   ```

3. **You must update:**
- `server.secret_key` — secret key for SearXNG (minimum 32 characters)
   
4. **Optional tweaks:**
- `adapter.searxng_url` — endpoint used to reach SearXNG
- `adapter.scraper.user_agent` — User-Agent header for scraping
- `adapter.scraper.max_content_length` — maximum raw content size
- `adapter.extract.*` — Tavily Extract API limits (URL cap, timeouts, default format)

## 💡 Using it as a Tavily drop-in

### Option 1: Python client (local)

```python
# Replace the original import
from simple_tavily_adapter.tavily_client import TavilyClient

# Use it exactly like the original Tavily client
client = TavilyClient()  # API key not required
response = client.search(
    query="bitcoin price",
    max_results=5,
    include_raw_content=True
)
print(response)
```

### Option 2: Call the HTTP API

```python
import requests

response = requests.post("http://localhost:8000/search", json={
    "query": "bitcoin price",
    "max_results": 5,
    "include_raw_content": True
})
print(response.json())
```

### Option 3: Switch base_url in the official Tavily client

```python
# Install the official client
# pip install tavily-python

from tavily import TavilyClient

# Change only the base_url
client = TavilyClient(
    api_key="unused",  # Key is ignored
    base_url="http://localhost:8000"  # Point to your adapter
)

response = client.search(
    query="bitcoin price",
    max_results=5,
    include_raw_content=True
)
```

### Option 4: Tavily Extract API

```bash
curl -X POST "http://localhost:8000/extract" \
     -H "Content-Type: application/json" \
     -d '{"urls": ["https://example.com"], "include_images": true}'
```

Returns markdown/text content, image metadata, and basic page info. The endpoint uses `crawl4ai`, so:
- **Docker**: the adapter image downloads Playwright Chromium during build (`playwright install chromium`).
- **Local**: run once:

```bash
cd simple_tavily_adapter
pip install -r requirements.txt
crawl4ai-setup  # installs Playwright browsers
```

## 🔄 Migrating from Tavily

Update your code as follows:

```python
# Before:
# client = TavilyClient("tvly-xxxxxxx")

# After:
client = TavilyClient()  # No API key needed
# OR
client = TavilyClient(base_url="http://localhost:8000")
```

Everything else **stays exactly the same**.

## Generating a secret key

```bash
# Option 1: Python
python3 -c "import secrets; print(secrets.token_hex(32))"

# Option 2: OpenSSL
openssl rand -hex 32

# Option 3: /dev/urandom
head -c 32 /dev/urandom | xxd -p -c 32
```

## Configuration structure

```yaml
# SearXNG settings (root level)
use_default_settings: true
server:
  secret_key: "YOUR_SECRET_KEY"
search:
  formats: [html, json, csv, rss]

# Tavily Adapter settings
adapter:
  searxng_url: "http://searxng:8080"
  server:
    port: 8000
  scraper:
    max_content_length: 2500
```

## Launch

```bash
docker-compose up -d
```

## ✅ Verify everything works

```bash
# SearXNG
curl "http://localhost:8999/search?q=test&format=json"

# Tavily Adapter
curl -X POST "http://localhost:8000/search" \
     -H "Content-Type: application/json" \
     -d '{"query": "test", "max_results": 3}'

curl -X POST "http://localhost:8000/extract" \
     -H "Content-Type: application/json" \
     -d '{"urls": "https://example.com", "format": "text"}'
```

## 📊 Response format

Fully compatible with the Tavily API:

```json
{
  "query": "bitcoin price",
  "follow_up_questions": null,
  "answer": null,
  "images": [],
  "results": [
    {
      "url": "https://example.com",
      "title": "Bitcoin Price",
      "content": "Bitcoin costs $50,000...",
      "score": 0.9,
      "raw_content": "Full page content..."
    }
  ],
  "response_time": 1.23,
  "request_id": "uuid-string"
}
```

## 🎯 Benefits

- ✅ **Free** — no API keys or request limits
- ✅ **Private** — searches run through your SearXNG instance
- ✅ **Compatible** — identical API to Tavily
- ✅ **Fast** — local deployment
- ✅ **In control** — choose and tune search engines
