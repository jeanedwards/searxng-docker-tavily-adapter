"""
Pydantic models for Tavily adapter API requests and responses.

This module contains all data models used by the FastAPI endpoints,
including request/response schemas for search and extract operations.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

# Import Tavily-compatible models from existing client
from .tavily_client import TavilyResponse, TavilyResult


class SearchRequest(BaseModel):
    """
    Request model for search endpoint.

    Attributes:
        query: Search query string
        max_results: Maximum number of results to return (default: 10)
        include_raw_content: Whether to scrape and include raw page content (default: False)
    """

    query: str
    max_results: int = 10
    include_raw_content: bool = False


class ExtractRequest(BaseModel):
    """
    Request model for extract endpoint.

    Attributes:
        urls: Single URL string or list of URLs to extract content from
        include_images: Whether to extract images from pages (default: False)
        include_links: Whether to preserve links in output (default: False)
        include_favicon: Whether to extract favicon URLs (default: False)
        extract_depth: Extraction mode - "basic" (fast) or "advanced" (thorough)
        format: Output format - "markdown" or "text"
        timeout: Per-URL timeout in seconds (optional, uses config defaults)
    """

    urls: list[str] | str
    include_images: bool = False
    include_links: bool = False
    include_favicon: bool = False
    extract_depth: Literal["basic", "advanced"] = "basic"
    format: Literal["markdown", "text"] | None = None
    timeout: float | None = None


class ExtractResult(BaseModel):
    """
    Single extraction result from a URL.

    Attributes:
        url: The extracted URL
        title: Page title (if available)
        language: Detected page language code
        raw_content: Extracted content in requested format
        images: List of extracted images (if requested)
        favicon: Favicon URL (if requested)
        metadata: Additional metadata from the crawl
    """

    url: str
    title: str | None = None
    language: str | None = None
    raw_content: str | None = None
    images: list[dict[str, Any]] = Field(default_factory=list)
    favicon: str | None = None
    metadata: dict[str, Any] | None = None


class ExtractResponse(BaseModel):
    """
    Response model for extract endpoint.

    Attributes:
        request_id: Unique identifier for this request
        response_time: Total processing time in seconds
        results: Successfully extracted results
        failed_results: URLs that failed extraction with error details
    """

    request_id: str
    response_time: float
    results: list[ExtractResult] = Field(default_factory=list)
    failed_results: list[dict[str, str]] = Field(default_factory=list)


# Re-export Tavily models for convenience
__all__ = [
    "SearchRequest",
    "ExtractRequest",
    "ExtractResult",
    "ExtractResponse",
    "TavilyResponse",
    "TavilyResult",
]
