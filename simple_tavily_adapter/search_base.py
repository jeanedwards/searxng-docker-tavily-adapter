"""Shared base class for search-related services."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from crawl4ai import AsyncWebCrawler

from .service_base import BaseService, CrawlContentMixin
from .utils import build_browser_config, build_search_crawl_config


class BaseSearchService(BaseService, CrawlContentMixin):
    """Shared helpers for search services that may scrape raw content."""

    async def _scrape_urls(self, urls: list[str]) -> tuple[dict[str, str], dict[str, Any]]:
        raw_contents: dict[str, str] = {}
        scraping_stats = {"total": len(urls), "success": 0, "failed": 0, "errors": {}}

        if not urls:
            return raw_contents, scraping_stats

        crawl_config = build_search_crawl_config()
        browser_config = build_browser_config()

        async with AsyncWebCrawler(config=browser_config) as crawler:
            tasks = [self._fetch_raw_content_crawl4ai(crawler, url, crawl_config) for url in urls]
            crawl_results = await asyncio.gather(*tasks, return_exceptions=True)

            for url, crawl_result in zip(urls, crawl_results, strict=True):
                if isinstance(crawl_result, Exception):
                    self.logger.warning("Unexpected error scraping %s: %s", url, crawl_result)
                    scraping_stats["failed"] += 1
                    error_type = type(crawl_result).__name__
                    errors_dict = scraping_stats["errors"]
                    if isinstance(errors_dict, dict):
                        errors_dict[error_type] = errors_dict.get(error_type, 0) + 1
                    continue

                content, error = crawl_result
                if content:
                    raw_contents[url] = content
                    scraping_stats["success"] += 1
                else:
                    scraping_stats["failed"] += 1
                    error_type = error or "unknown"
                    errors_dict = scraping_stats["errors"]
                    if isinstance(errors_dict, dict):
                        errors_dict[error_type] = errors_dict.get(error_type, 0) + 1
                    self.logger.debug("Failed to scrape %s: %s", url, error_type)

        self.logger.info(
            "Raw content scraping: %s/%s successful, %s failed. Errors: %s",
            scraping_stats["success"],
            scraping_stats["total"],
            scraping_stats["failed"],
            dict(scraping_stats["errors"]),
        )
        return raw_contents, scraping_stats
