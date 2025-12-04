# Networking Guide for Local Development

## Overview

This guide explains how networking works when developing the SearXNG Tavily Adapter locally.

## Architecture

### Docker Deployment (Production)
```
┌─────────────────────────────────────────┐
│         Docker Network (searxng)        │
│                                         │
│  ┌──────────┐  ┌──────────┐  ┌───────┐ │
│  │ Adapter  │→ │ SearXNG  │→ │ Redis │ │
│  │ :8001    │  │ :8080    │  │ :6379 │ │
│  └──────────┘  └──────────┘  └───────┘ │
│       │                                 │
└───────┼─────────────────────────────────┘
        │
        ▼
   Host :8001
```

**Connections:**
- Adapter → SearXNG: `http://searxng:8080` (Docker DNS)
- SearXNG → Redis: `redis://redis:6379` (Docker DNS)
- External → Adapter: `http://localhost:8001`

**Config:** Use `config.example.yaml` with `searxng_url: "http://searxng:8080"`

---

### Local Development (Hybrid)
```
┌──────────────────────────────────────────┐
│  Host Machine                            │
│                                          │
│  ┌──────────────┐                        │
│  │   Adapter    │                        │
│  │  (Python)    │                        │
│  │   :8001      │                        │
│  └──────┬───────┘                        │
│         │                                │
│         │ http://localhost:8999          │
│         │ (port mapping)                 │
│         ▼                                │
│  ┌─────────────────────────────────────┐ │
│  │  Docker Network (searxng)           │ │
│  │                                     │ │
│  │  ┌──────────┐          ┌───────┐   │ │
│  │  │ SearXNG  │   ──→   │ Redis │   │ │
│  │  │ :8080    │          │ :6379 │   │ │
│  │  └────┬─────┘          └───────┘   │ │
│  │       │                            │ │
│  └───────┼────────────────────────────┘ │
│          │ 0.0.0.0:8999 → :8080         │
└──────────┼──────────────────────────────┘
           │
           ▼
     External Access
     localhost:8999
```

**Connections:**
- Adapter → SearXNG: `http://localhost:8999` (port mapping)
- SearXNG → Redis: `redis://redis:6379` (Docker DNS)
- External → SearXNG: `http://localhost:8999`
- External → Adapter: `http://localhost:8001`

**Config:** Use `config.local.yaml` with `searxng_url: "http://localhost:8999"`

---

## Configuration Files

### For Docker (Production)

**`config.example.yaml`:**
```yaml
adapter:
  searxng_url: "http://searxng:8080"  # Docker internal DNS
```

**`docker-compose.yaml`:**
- All services on same Docker network
- Only adapter port exposed: `8001:8001`
- SearXNG accessible internally

**Usage:**
```bash
docker compose up -d
```

### For Local Development

**`config.local.yaml`:**
```yaml
adapter:
  searxng_url: "http://localhost:8999"  # Host port mapping
```

**`docker-compose.yaml` + `docker-compose.local.yaml`:**
- Base + override configuration
- SearXNG port exposed: `8999:8080`
- Redis port exposed: `6379:6379` (for future use)
- Adapter runs on host, not in Docker

**Usage:**
```bash
# Start Docker services only
make docker-up
# or
docker compose -f docker-compose.yaml -f docker-compose.local.yaml up -d searxng redis

# Run adapter on host
make run
# or
uv run uvicorn simple_tavily_adapter.main:app --reload
```

---

## Port Mappings

| Service | Container Port | Host Port | Access From Host |
|---------|---------------|-----------|------------------|
| SearXNG | 8080 | 8999 | http://localhost:8999 |
| Redis | 6379 | 6379 | localhost:6379 |
| Adapter (Docker) | 8001 | 8001 | http://localhost:8001 |
| Adapter (Local) | 8001 | 8001 | http://localhost:8001 |

---

## Common Scenarios

### Scenario 1: Full Docker Stack
**Use Case:** Production, testing complete stack

```bash
docker compose up -d
curl http://localhost:8001/search -d '{"query":"test"}' -H 'Content-Type: application/json'
```

**Config:** `config.example.yaml` → `config.yaml`
- `searxng_url: "http://searxng:8080"`

---

### Scenario 2: Local Adapter Development
**Use Case:** Developing adapter features, hot-reload

```bash
make docker-up  # Start SearXNG + Redis
make run        # Run adapter locally
```

**Config:** `config.local.yaml` → `config.yaml`
- `searxng_url: "http://localhost:8999"`

---

### Scenario 3: Testing SearXNG Directly
**Use Case:** Debugging SearXNG issues

```bash
make docker-up
curl "http://localhost:8999/search?q=test&format=json"
```

No adapter needed.

---

## Troubleshooting

### Problem: Connection Refused

**Symptom:**
```
aiohttp.client_exceptions.ClientConnectorError: Cannot connect to host searxng:8080
```

**Cause:** Using Docker internal URL (`searxng:8080`) when running adapter locally.

**Solution:**
```bash
# Check your config
grep searxng_url config.yaml

# Should be:
searxng_url: "http://localhost:8999"  # For local development

# NOT:
searxng_url: "http://searxng:8080"    # Only for Docker
```

---

### Problem: SearXNG Not Responding

**Symptom:**
```
curl: (7) Failed to connect to localhost port 8999: Connection refused
```

**Cause:** SearXNG container not running or port not exposed.

**Solution:**
```bash
# Check if running
docker compose ps

# Start with local config
make docker-up

# Verify port mapping
docker compose -f docker-compose.yaml -f docker-compose.local.yaml ps
# Should show: 0.0.0.0:8999->8080/tcp

# Check logs
docker compose logs searxng
```

---

### Problem: Wrong Compose File

**Symptom:**
```
docker compose ps shows no port mapping for 8999
```

**Cause:** Started with base compose file only.

**Solution:**
```bash
# Stop containers
docker compose down

# Start with local development setup
make docker-up
# This uses both docker-compose.yaml and docker-compose.local.yaml
```

---

## Best Practices

### For Local Development

1. **Always use `make docker-up`** instead of `docker compose up`
   - Ensures correct compose files are used
   - Exposes necessary ports

2. **Use `config.local.yaml` as template**
   - Pre-configured for localhost access
   - Copy to `config.yaml` and edit secret_key

3. **Verify connectivity before running adapter**
   ```bash
   curl http://localhost:8999/search?q=test&format=json
   ```

### For Production/Docker

1. **Use `docker compose up -d`** (no local override)
   - Uses Docker internal networking
   - Better isolation

2. **Use `config.example.yaml` as template**
   - Pre-configured for Docker DNS
   - Copy to `config.yaml` and edit

3. **All services in one stack**
   - No host networking needed
   - Simpler deployment

---

## Quick Reference

### Local Development Commands
```bash
make docker-up          # Start SearXNG + Redis (with ports)
make run                # Run adapter locally
make docker-down        # Stop all
curl http://localhost:8999/search?q=test&format=json  # Test SearXNG
curl http://localhost:8001/health  # Test adapter
```

### Docker Commands
```bash
docker compose up -d                    # Full stack
docker compose logs -f adapter          # View logs
docker compose down                     # Stop all
```

### Config Check
```bash
# For local development
grep searxng_url config.yaml
# Should output: searxng_url: "http://localhost:8999"

# For Docker
grep searxng_url config.yaml
# Should output: searxng_url: "http://searxng:8080"
```

---

## Summary

| Aspect | Local Development | Docker Deployment |
|--------|------------------|-------------------|
| Adapter Location | Host machine | Docker container |
| SearXNG Access | localhost:8999 | searxng:8080 |
| Config File | config.local.yaml | config.example.yaml |
| Compose Files | base + local | base only |
| Command | `make docker-up` | `docker compose up` |
| Use Case | Development | Production |

