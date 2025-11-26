import pathlib
import sys

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

# Ensure repo root on sys.path for direct module imports when running tests locally.
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from simple_tavily_adapter.config_loader import config
from simple_tavily_adapter.models import ExtractRequest, SearchRequest
from simple_tavily_adapter.scraper_service import ExtractService
from simple_tavily_adapter.searx_search_service import SearchService


class _StubSearxClient:
    async def search(self, params):
        return {
            "results": [
                {"url": "https://example.com", "title": "Example", "content": "snippet"},
                {"url": "https://example.org", "title": "Example Org", "content": "snippet"},
            ]
        }


class _NoScrapeSearchService(SearchService):
    """SearchService variant that skips crawling for deterministic tests."""

    async def _scrape_urls(self, urls):  # type: ignore[override]
        return {}, {"total": len(urls), "success": 0, "failed": 0, "errors": {}}


@pytest.mark.asyncio
async def test_search_service_returns_results_without_scraping():
    service = _NoScrapeSearchService(client=_StubSearxClient())
    request = SearchRequest(query="test", max_results=2, include_raw_content=False)

    result = await service.search(request)

    assert result["query"] == "test"
    assert len(result["results"]) == 2
    assert all("url" in r for r in result["results"])


@pytest.mark.asyncio
async def test_extract_service_rejects_empty_urls():
    service = ExtractService()
    request = ExtractRequest(urls=[], format="markdown", include_images=False, include_favicon=False)
    with pytest.raises(HTTPException) as exc:
        await service.extract(request)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_extract_service_rejects_too_many_urls():
    service = ExtractService()
    too_many = [f"https://example.com/{i}" for i in range(config.extract_max_urls + 1)]
    request = ExtractRequest(urls=too_many, format="markdown", include_images=False, include_favicon=False)
    with pytest.raises(HTTPException) as exc:
        await service.extract(request)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_extract_service_rejects_invalid_format():
    with pytest.raises(ValidationError):
        ExtractRequest(urls=["https://example.com"], format="html", include_images=False, include_favicon=False)
