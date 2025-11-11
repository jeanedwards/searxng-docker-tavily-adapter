# SearXNG Tavily Adapter — Developer Wiki Summary

## What This Project Is
- Internal replacement for the commercial Tavily API built on top of the self-hosted SearXNG metasearch engine.
- Provides the same search/extract endpoints Tavily-compatible clients expect, but keeps all traffic, logs, and credentials inside our infrastructure.
- Ships as a ready-to-run Docker Compose stack plus a lightweight FastAPI service for local development and testing via `uv`.

## Why We Need It
- **Cost & rate-limit control:** Eliminates external API quotas by letting us scale searches with our own hardware.
- **Privacy & compliance:** Queries never leave our environment, which helps with SOC2/GDPR requirements when analysts run investigative or internal data lookups.
- **Integration flexibility:** Any tooling that already talks to Tavily (agents, RAG pipelines, browsers) can point to this adapter without code changes.
- **Deployment parity:** The same configuration works for laptops (developer testing), Docker Compose (lab/POC), and Azure Container Apps (production).

## How It Works (High Level)
1. Clients hit the FastAPI adapter on port 8000 using Tavily-style `/search` and `/extract` calls.
2. The adapter translates the payload into a SearXNG meta-search request and streams the results back in Tavily’s JSON shape.
3. Redis provides short-lived caching for repeated queries and helps coordinate rate limiting when running multiple replicas.
4. In Azure Container Apps the adapter, Redis, and SearXNG run as sidecars inside one Container App; only the adapter ingress is exposed.

## How to Use It
- **Production / shared environments (recommended):**
  - Copy `config.example.yaml` to `config.yaml`, set a unique `secret_key`, then run `docker compose up -d` to bring up SearXNG, Redis, and the adapter together.
  - Verify with `curl http://localhost:8000/health` and a sample `/search` request.
- **Developer laptops (fast iteration):**
  - Run `./setup-local.sh` (or `setup-local.ps1`) once, then `make docker-up` to start SearXNG + Redis and `make run` for a hot-reload adapter connected to `http://localhost:8999`.
  - Keep configs in `config.local.yaml` → `config.yaml` for localhost defaults.
- **Azure deployment:**
  - Use the provided GitHub Actions workflow; supply `CONFIG_YAML`, `SEARXNG_SECRET_KEY`, and Azure credentials as repository secrets, then trigger “Deploy to Azure Container Apps.”

## Azure Rollout Details
- **Topology:** One Azure Container App hosts three containers (adapter, Redis, SearXNG) that share the same VNet namespace; only port 8000 from the adapter faces the public ingress.
- **Secrets & config:** `CONFIG_YAML` (usually derived from `config.azure.yaml`) and `SEARXNG_SECRET_KEY` are stored as GitHub repository secrets; the workflow injects them as Dapr secrets for the Container App environment.
- **CI/CD path:** The `Deploy to Azure Container Apps` workflow builds the adapter image, pushes it to Azure Container Registry, updates the Container App revision, and restarts pods with zero downtime thanks to ACA’s rolling upgrade.
- **Observability:** ACA health probes hit `/health` automatically; application logs stream to Log Analytics, while container metrics (CPU/memory) drive built-in autoscaling rules (default 1–3 replicas).
- **Recovery:** Because Redis uses ephemeral storage, scaling to zero or restarting clears the cache but not search functionality; for persistent logs or backups, wire ACA to Azure Blob or an external Redis instance.

## Operational Notes
- `pyproject.toml` + `uv.lock` define dependencies for development; CI regenerates `simple_tavily_adapter/requirements.txt` for Docker builds.
- The adapter logs enough detail for debugging but avoids storing query content; production secrets stay in `config.azure.yaml`/GitHub secrets.
- Health checks: `/health` for liveness, `/search` with a short query for end-to-end verification.
- Common troubleshooting: ensure Docker ports 8000 (adapter) and 8999 (SearXNG) are free, and confirm Redis is reachable when rate limiting misbehaves.

This document intentionally stays high level so it can live on the internal developer wiki; link to `README.md`, `LOCAL_DEVELOPMENT.md`, and `AZURE_DEPLOYMENT.md` for deeper instructions when needed.
