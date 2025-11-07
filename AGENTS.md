# Repository Guidelines

## Project Structure & Module Organization
- `docker-compose.yaml` defines the SearXNG + adapter + Redis stack; keep `config.yaml` in sync with `CONFIG_SETUP.md` before lifting services.
- `simple_tavily_adapter/` holds the FastAPI app (`main.py`), config loader, client stub, and lightweight test script; vendor deps are pinned in `requirements.txt`.
- `searxng/limiter.toml` and `Caddyfile` tune upstream rate limits and HTTPS/front-proxy headers; only edit these when changing traffic policies.
- Service assets such as `searxng-docker.service.template` support systemd deployments—update them when altering unit names or bind mounts.

## Build, Test, and Development Commands
- Bootstrap config: `cp config.example.yaml config.yaml && nano config.yaml` to set `secret_key`, adapter host/port, and scraper caps.
- Bring up the full stack: `docker compose up -d` (use `docker compose logs -f adapter` when debugging FastAPI) and `docker compose down` for teardown.
- Adapter-only loop: `cd simple_tavily_adapter && pip install -r requirements.txt && uvicorn main:app --host 0.0.0.0 --port 8000 --reload` to iterate without Docker.
- Compatibility smoke test: `cd simple_tavily_adapter && python test_client.py` to hit `/search`; complement with `curl -X POST http://localhost:8000/search -d '{"query":"ping"}' -H 'Content-Type: application/json'` for quick regression checks.

## Coding Style & Naming Conventions
- Follow idiomatic Python 3.11+, async-first FastAPI patterns, and 4-space indentation; prefer snake_case for symbols and descriptive request/response models.
- Keep type hints and Pydantic models (`TavilyResult`, `SearchRequest`) in sync with Tavily’s schema; log in English for observability and stick to structured f-strings.
- Run `ruff check .` or `black .` before commits if you add lint/format configs; keep Dockerfiles and YAML declarative with lowercase keys.

## Testing Guidelines
- Target high-level compatibility: use `python test_client.py` for client-side validation and `docker compose exec adapter pytest` if you introduce unit suites.
- New scraping logic must include a fixture or mocked aiohttp session; document edge cases inside `tests/` with names like `test_<feature>.py`.
- Validate readiness endpoints via `curl http://localhost:8000/health` and confirm Redis/SearXNG connectivity before marking changes ready.

## Commit & Pull Request Guidelines
- Mirror the existing Conventional Commits style (`feat: ...`, `fix: ...`, `docs: ...`); keep summaries under 72 chars and include motivating context in the body when needed.
- Every PR should link the relevant issue, describe config changes, attach `docker compose ps`/curl excerpts, and mention any follow-up migration steps; screenshots help when UI/Caddy headers change.

## Security & Configuration Tips
- Never commit real `config.yaml`; rely on `config.example.yaml` for defaults and document secrets in `CONFIG_SETUP.md`.
- Treat `config_loader.py` defaults as fallback only—production deployments must point `adapter.searxng_url` to the internal network and rotate scraper user agents to avoid bans.
- When exposing ports beyond localhost, ensure Caddy or another proxy enforces TLS and align `searxng/limiter.toml` with expected query volume.
