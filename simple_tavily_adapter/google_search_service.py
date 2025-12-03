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

# Max retries for transient connection errors.
_MAX_RETRIES = 3
# Base delay between retries in seconds (exponential backoff).
_RETRY_DELAY_BASE = 0.5
# Serialize Google API calls. httplib2 isn't thread-safe, so we process
# requests one at a time to avoid timeouts and SSL errors.
_MAX_CONCURRENT_REQUESTS = 1


class GoogleSearchService(BaseSearchService):
    """Service for performing searches via Google Custom Search API."""

    def __init__(self, logger: logging.Logger | None = None):
        super().__init__(logger=logger)
        self._service = None
        # Semaphore to limit concurrent Google API calls.
        self._semaphore = asyncio.Semaphore(_MAX_CONCURRENT_REQUESTS)

    def _get_service(self, force_new: bool = False):
        """
        Get or create Google Custom Search API service.

        Args:
            force_new: If True, recreate the service even if cached.
                       Useful after SSL connection errors.
        """
        if self._service is None or force_new:
            if not config.google_api_key:
                raise HTTPException(
                    status_code=500,
                    detail="Google API not configured. Set GOOGLE_API_KEY.",
                )
            from googleapiclient.discovery import build

            # Clear cached service before creating new one.
            self._service = None
            self._service = build(
                "customsearch",
                "v1",
                developerKey=config.google_api_key,
                cache_discovery=False,
            )
        return self._service

    def _is_retryable_error(self, exc: Exception) -> bool:
        """Check if exception is a transient error that can be retried."""
        error_str = str(exc).lower()
        # Check for common transient connection/SSL errors.
        retryable_indicators = [
            "ssl",
            "record layer failure",
            "connection reset",
            "connection aborted",
            "broken pipe",
            "timed out",
            "timeout",
        ]
        return any(indicator in error_str for indicator in retryable_indicators)

    def _execute_google_search(self, query: str, num_results: int) -> dict[str, Any]:
        """
        Execute Google search with retry logic for transient SSL errors.

        The googleapiclient uses httplib2 which can have SSL connection
        issues under rapid concurrent requests. This method retries with
        a fresh connection on SSL errors.
        """
        last_error = None

        for attempt in range(_MAX_RETRIES):
            try:
                # Force new service on retry attempts to get fresh connection.
                service = self._get_service(force_new=(attempt > 0))
                return (
                    service.cse()
                    .list(
                        cx=config.google_cse_id,
                        q=query,
                        num=min(num_results, 10),
                    )
                    .execute()
                )
            except Exception as exc:
                last_error = exc
                # Only retry on transient connection errors.
                if self._is_retryable_error(exc) and attempt < _MAX_RETRIES - 1:
                    delay = _RETRY_DELAY_BASE * (2**attempt)
                    self.logger.warning(
                        "Transient error on attempt %d/%d, retrying in %.1fs: %s",
                        attempt + 1,
                        _MAX_RETRIES,
                        delay,
                        str(exc),
                    )
                    # Reset service to force new connection on next attempt.
                    self._service = None
                    time.sleep(delay)
                else:
                    # Non-SSL error or final attempt, re-raise.
                    raise

        # Should not reach here, but raise last error if we do.
        raise last_error  # type: ignore[misc]

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
            # Use semaphore to limit concurrent API calls.
            # httplib2 isn't thread-safe, causing timeouts/SSL errors under load.
            async with self._semaphore:
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
            urls_to_scrape = [
                r["link"] for r in google_results[: request.max_results] if r.get("link")
            ]
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

        self.logger.info(
            "Google search completed: %s results in %.2fs", len(results), response_time
        )
        return response.model_dump()
