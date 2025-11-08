"""
FastAPI route handlers for Tavily adapter endpoints.

This module defines the HTTP API layer with thin route handlers that
delegate business logic to service classes. Handles HTTP-specific
concerns like status codes and error responses.
"""
import logging
from typing import Any

from fastapi import APIRouter

from .models import SearchRequest, ExtractRequest
from .services import SearchService, ExtractService

# Initialize logger for routes
logger = logging.getLogger(__name__)

# Create API router
router = APIRouter()

# Initialize services
search_service = SearchService(logger=logger)
extract_service = ExtractService(logger=logger)


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
    return await search_service.search(request)


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

