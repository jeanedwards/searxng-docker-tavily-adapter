"""Search service implementation backed by Google Custom Search API."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any

from fastapi import HTTPException

from .config_loader import config
from .models import SearchRequest, TavilyResponse, TavilyResult
from .search_base import BaseSearchService


class GoogleSearchService(BaseSearchService):
    """Service for performing searches via Google Custom Search API."""

    def __init__(self, logger: logging.Logger | None = None):
        super().__init__(logger=logger)
        self._service = None

    def _get_service(self):
        if self._service is None:
            if not config.google_api_key:
                raise HTTPException(
                    status_code=500,
                    detail="Google API not configured. Set GOOGLE_API_KEY.",
                )
            from googleapiclient.discovery import build

            self._service = build(
                "customsearch",
                "v1",
                developerKey=config.google_api_key,
                cache_discovery=False,
            )
        return self._service

    def _execute_google_search(self, query: str, num_results: int) -> dict[str, Any]:
        service = self._get_service()
        return (
            service.cse()
            .list(
                cx=config.google_cse_id,
                q=query,
                num=min(num_results, 10),
            )
            .execute()
        )

    async def search(self, request: SearchRequest) -> dict[str, Any]:
        start_time = time.time()
        request_id = str(uuid.uuid4())

        self.logger.info("Google search request: %s", request.query)

        if not config.google_api_key or not config.google_cse_id:
            self.logger.error("Google API key or CSE ID not configured")
            raise HTTPException(
                status_code=500,
                detail="Google API not configured. Set GOOGLE_API_KEY and GOOGLE_CSE_ID.",
            )

        try:
            google_data = await asyncio.to_thread(
                self._execute_google_search,
                request.query,
                request.max_results,
            )
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001 - surface SDK errors with context
            error_msg = str(exc)
            self.logger.error("Google API error: %s", error_msg)

            if "403" in error_msg or "Forbidden" in error_msg:
                raise HTTPException(
                    status_code=500,
                    detail="Google API authentication failed. Check your API key.",
                ) from exc
            if "429" in error_msg or "Rate Limit" in error_msg:
                raise HTTPException(
                    status_code=429,
                    detail="Google API rate limit exceeded",
                ) from exc
            if "400" in error_msg or "Invalid" in error_msg:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid Google API request: {error_msg}",
                ) from exc

            raise HTTPException(
                status_code=500,
                detail="Google search service unavailable",
            ) from exc

        google_results = google_data.get("items", [])

        raw_contents: dict[str, str] = {}
        if request.include_raw_content and google_results:
            urls_to_scrape = [r["link"] for r in google_results[: request.max_results] if r.get("link")]
            raw_contents, _ = await self._scrape_urls(urls_to_scrape)

        results: list[TavilyResult] = []
        for i, result in enumerate(google_results[: request.max_results]):
            url = result.get("link")
            if not url:
                continue

            tavily_result = TavilyResult(
                url=url,
                title=result.get("title", ""),
                content=result.get("snippet", ""),
                score=0.9 - (i * 0.05),
                raw_content=raw_contents.get(url) if request.include_raw_content else None,
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

        self.logger.info("Google search completed: %s results in %.2fs", len(results), response_time)
        return response.model_dump()
