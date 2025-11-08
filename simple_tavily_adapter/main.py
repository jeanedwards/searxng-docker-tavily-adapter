"""
FastAPI application entry point for SearXNG Tavily Adapter.

This is the main application file that initializes the FastAPI app,
configures logging, and registers routes. The actual business logic
is implemented in separate modules (services, utils, models).
"""
import logging

from fastapi import FastAPI

from .config_loader import config
from .routes import router

# Configure logging for the application
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title="SearXNG Tavily Adapter",
    version="1.0.0",
    description="Tavily-compatible API powered by SearXNG and Crawl4AI"
)

# Register routes
app.include_router(router)


@app.on_event("startup")
async def startup_event():
    """
    Application startup handler.
    
    Logs configuration and performs any necessary initialization.
    """
    logger.info("Starting SearXNG Tavily Adapter")
    logger.info(f"SearXNG URL: {config.searxng_url}")
    logger.info(f"Server: {config.server_host}:{config.server_port}")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown handler.
    
    Performs cleanup operations before shutdown.
    """
    logger.info("Shutting down SearXNG Tavily Adapter")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=config.server_host,
        port=config.server_port,
        log_level="info"
    )
