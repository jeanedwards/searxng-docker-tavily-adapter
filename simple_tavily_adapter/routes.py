"""
FastAPI route handlers for Tavily adapter endpoints.

This module defines the HTTP API layer with thin route handlers that
delegate business logic to service classes. Handles HTTP-specific
concerns like status codes and error responses.
"""
import logging
from typing import Any

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from .cache import ResponseCache
from .config_loader import config
from .models import SearchRequest, ExtractRequest
from .services import SearchService, ExtractService

# Initialize logger for routes
logger = logging.getLogger(__name__)

# Create API router
router = APIRouter()

# Initialize services
search_service = SearchService(logger=logger)
extract_service = ExtractService(logger=logger)
# Response cache stores serialized bodies keyed by request payload.
search_response_cache = ResponseCache(
    max_entries=config.search_response_cache_max_entries,
    ttl_seconds=config.search_response_cache_ttl,
)


@router.post("/search")
async def search(request: SearchRequest) -> dict[str, Any]:
    """
    Tavily-compatible search endpoint.
    
    Performs web search via SearXNG backend with optional content scraping.
    Returns results in Tavily-compatible format.
    
    Args:
        request: SearchRequest with query and options
        
    Returns:
        TavilyResponse dictionary with search results
        
    Raises:
        HTTPException: On SearXNG errors or timeouts
    """
    cache_key = (request.query, request.max_results, request.include_raw_content)

    # Serve cached response when available to bypass downstream service work.
    cached_response = await search_response_cache.get(cache_key)
    if cached_response is not None:
        logger.debug("Serving cached /search response for query=%s", request.query)
        return cached_response

    response_payload = await search_service.search(request)
    # Store response so consecutive identical requests reuse it.
    await search_response_cache.set(cache_key, response_payload)
    return response_payload


@router.post("/extract")
async def extract(request: ExtractRequest) -> dict[str, Any]:
    """
    Tavily-compatible extract endpoint powered by Crawl4AI.
    
    Extracts content from one or more URLs with configurable depth,
    format, and metadata extraction.
    
    Args:
        request: ExtractRequest with URLs and extraction options
        
    Returns:
        ExtractResponse dictionary with extracted content
        
    Raises:
        HTTPException: On invalid parameters or extraction errors
    """
    return await extract_service.extract(request)


@router.get("/health")
async def health() -> dict[str, str]:
    """
    Health check endpoint.
    
    Simple endpoint to verify service is running and responsive.
    
    Returns:
        Dictionary with status and service name
    """
    return {"status": "ok", "service": "searxng-tavily-adapter"}


@router.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt() -> str:
    """
    Robots exclusion file route.
    
    Returns a static robots.txt that tells crawlers to skip all paths.
    This keeps search engines from indexing any endpoint of the adapter.
    
    Returns:
        Simple string with robots directives
    """
    # Disallow everything so crawlers stay away from the API.
    return "User-agent: *\nDisallow: /"

