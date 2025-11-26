"""Shared service helpers and base classes.

Provides lightweight base classes to give all services consistent logging
and shared crawl helpers without coupling them to HTTP or FastAPI layers.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from crawl4ai import AsyncWebCrawler

from .config_loader import config
from .utils import safe_markdown


class BaseService:
    """Base class that provides a logger for derived services."""

    def __init__(self, logger: logging.Logger | None = None):
        # Use module-qualified name so loggers stay readable when subclassed
        self.logger = logger or logging.getLogger(self.__class__.__module__)


class CrawlContentMixin:
    """Reusable crawl helper for services that need raw page content."""

    async def _fetch_raw_content_crawl4ai(
        self,
        crawler: AsyncWebCrawler,
        url: str,
        config_obj: Any,
    ) -> tuple[str | None, str | None]:
        """
        Scrape a page using Crawl4AI and return markdown content.

        Returns (markdown_content, error_message). On success error_message is None,
        otherwise markdown_content is None.
        """
        try:
            crawl_future = crawler.arun(url=url, config=config_obj)
            crawl_result = await asyncio.wait_for(
                crawl_future,
                timeout=config.scraper_timeout + 2,
            )
        except TimeoutError:
            return None, "timeout"
        except Exception as exc:  # noqa: BLE001 - bubble unexpected crawl errors
            self.logger.warning("Crawl error for %s: %s", url, exc)
            return None, "crawl_failed"

        if not getattr(crawl_result, "success", False):
            error_msg = getattr(crawl_result, "error_message", "unknown_error") or "unknown_error"
            return None, error_msg

        markdown = safe_markdown(getattr(crawl_result, "markdown", None))
        if not markdown:
            return None, "no_content"

        if len(markdown) > config.scraper_max_length:
            markdown = markdown[: config.scraper_max_length] + "..."

        return markdown, None
