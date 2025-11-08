"""
FastAPI application entry point for SearXNG Tavily Adapter.

This is the main application file that initializes the FastAPI app,
configures logging, and registers routes. The actual business logic
is implemented in separate modules (services, utils, models).
"""
import logging
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response

from .config_loader import config
from .routes import router

# Configure logging for the application
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """
    FastAPI lifespan handler.

    Replaces deprecated startup/shutdown events while keeping the same
    logging and initialization semantics. Enter yields control to the app,
    exit performs clean shutdown logging.
    """
    _ = app  # Documenting the app instance is available if initialization needs it later.
    logger.info("Starting SearXNG Tavily Adapter")
    logger.info(f"SearXNG URL: {config.searxng_url}")
    logger.info(f"Server: {config.server_host}:{config.server_port}")
    try:
        yield
    finally:
        logger.info("Shutting down SearXNG Tavily Adapter")


# Initialize FastAPI application
app = FastAPI(
    title="SearXNG Tavily Adapter",
    version="1.0.0",
    description="Tavily-compatible API powered by SearXNG and Crawl4AI",
    lifespan=app_lifespan,
)

# Register routes
app.include_router(router)


@app.middleware("http")
async def add_noindex_header(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """
    Middleware that adds X-Robots-Tag header to every response.

    This discourages search engines and other automated indexers from storing
    our responses. It keeps the API surface out of public search listings
    while still serving legitimate clients normally.
    """
    response = await call_next(request)
    # Add an explicit noindex directive to every response for safety.
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=config.server_host,
        port=config.server_port,
        log_level="info",
    )
