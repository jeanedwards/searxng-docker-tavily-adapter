"""Compatibility façade for service classes.

Re-exports focused implementations from dedicated modules to keep imports
stable while the codebase remains modular.
"""

from .google_search_service import GoogleSearchService
from .scraper_service import ExtractService
from .searx_search_service import SearchService

__all__ = ["SearchService", "GoogleSearchService", "ExtractService"]
