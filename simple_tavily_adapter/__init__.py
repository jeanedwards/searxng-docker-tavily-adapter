"""
SearXNG Tavily Adapter package.

A FastAPI application that provides Tavily-compatible API using SearXNG
as the search backend and Crawl4AI for content extraction.
"""
from .main import app

__version__ = "1.0.0"
__all__ = ["app"]

