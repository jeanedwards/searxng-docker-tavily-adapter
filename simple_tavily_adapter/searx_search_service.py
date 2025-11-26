"""Search service implementation backed by SearXNG."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from .models import SearchRequest, TavilyResponse, TavilyResult
from .search_base import BaseSearchService
from .searxng_client import SearxngClient


class SearchService(BaseSearchService):
    """Service for performing searches via SearXNG backend."""

    def __init__(self, logger: logging.Logger | None = None, client: SearxngClient | None = None):
        super().__init__(logger=logger)
        self.client = client or SearxngClient(logger=self.logger)

    async def search(self, request: SearchRequest) -> dict[str, Any]:
        start_time = time.time()
        request_id = str(uuid.uuid4())

        self.logger.info("Search request: %s", request.query)

        searxng_params = {
            "q": request.query,
            "format": "json",
            "categories": "general",
            "engines": "google,duckduckgo,brave",
            "pageno": 1,
            "language": "auto",
            "safesearch": 1,
        }

        searxng_data = await self.client.search(searxng_params)
        searxng_results = searxng_data.get("results", [])

        raw_contents: dict[str, str] = {}
        if request.include_raw_content and searxng_results:
            urls_to_scrape = [r["url"] for r in searxng_results[: request.max_results] if r.get("url")]
            raw_contents, _ = await self._scrape_urls(urls_to_scrape)

        results: list[TavilyResult] = []
        for i, result in enumerate(searxng_results[: request.max_results]):
            if not result.get("url"):
                continue

            tavily_result = TavilyResult(
                url=result["url"],
                title=result.get("title", ""),
                content=result.get("content", ""),
                score=0.9 - (i * 0.05),
                raw_content=raw_contents.get(result["url"]) if request.include_raw_content else None,
            )
            results.append(tavily_result)

        response_time = time.time() - start_time
        response = TavilyResponse(
            query=request.query,
            follow_up_questions=None,
            answer=None,
            images=[],
            results=results,
            response_time=response_time,
            request_id=request_id,
        )

        self.logger.info("Search completed: %s results in %.2fs", len(results), response_time)
        return response.model_dump()
