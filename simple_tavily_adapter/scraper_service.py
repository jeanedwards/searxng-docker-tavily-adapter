"""Extraction service backed by Crawl4AI and PDF utilities."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any

from crawl4ai import AsyncWebCrawler
from fastapi import HTTPException

from .config_loader import config
from .models import ExtractRequest, ExtractResponse, ExtractResult
from .service_base import BaseService
from .utils import (
    build_browser_config,
    build_run_config,
    coerce_url_list,
    detect_language,
    extract_images,
    extract_pdf_text,
    extract_pdf_title,
    guess_favicon,
    is_pdf_url,
    render_crawl_body,
    resolve_title,
    serialize_metadata,
)


class ExtractService(BaseService):
    """Service for extracting content from URLs using Crawl4AI."""

    def __init__(self, logger: logging.Logger | None = None):
        super().__init__(logger=logger)

    async def extract(self, request: ExtractRequest) -> dict[str, Any]:
        urls = coerce_url_list(request.urls)
        if not urls:
            raise HTTPException(status_code=400, detail="At least one URL is required")
        if len(urls) > config.extract_max_urls:
            raise HTTPException(
                status_code=400,
                detail=f"Too many URLs. Max allowed: {config.extract_max_urls}",
            )

        preferred_format = (request.format or config.extract_default_format).lower()
        if preferred_format not in {"markdown", "text"}:
            raise HTTPException(status_code=400, detail="format must be 'markdown' or 'text'")

        per_url_timeout = request.timeout or (
            config.extract_timeout_advanced
            if request.extract_depth == "advanced"
            else config.extract_timeout_basic
        )

        run_config = build_run_config(request.extract_depth, per_url_timeout)
        request_id = str(uuid.uuid4())
        start_time = time.time()
        results: list[ExtractResult] = []
        failed: list[dict[str, str]] = []

        pdf_urls = [url for url in urls if is_pdf_url(url)]
        html_urls = [url for url in urls if not is_pdf_url(url)]

        for url in pdf_urls:
            self.logger.debug("Extracting PDF: %s", url)
            pdf_text, pdf_error = await extract_pdf_text(
                url, timeout=per_url_timeout, max_size_mb=50.0
            )

            if pdf_error:
                self.logger.warning("PDF extraction failed for %s: %s", url, pdf_error)
                failed.append({"url": url, "error": pdf_error})
                continue

            title = extract_pdf_title(url)
            extract_result = ExtractResult(
                url=url,
                title=title,
                language=None,
                raw_content=pdf_text,
                images=[],
                favicon=None,
                metadata={"source": "pdf", "extractor": "pymupdf"},
            )
            results.append(extract_result)

        if html_urls:
            browser_config = build_browser_config()
            async with AsyncWebCrawler(config=browser_config) as crawler:
                for url in html_urls:
                    try:
                        crawl_future = crawler.arun(url=url, config=run_config)
                        crawl_result = await asyncio.wait_for(
                            crawl_future,
                            timeout=per_url_timeout + 2,
                        )
                    except TimeoutError:
                        self.logger.warning("Extract timeout for %s", url)
                        failed.append({"url": url, "error": "timeout"})
                        continue
                    except Exception as exc:  # noqa: BLE001 - keep behavior but add context
                        self.logger.error("Extract error for %s: %s", url, exc)
                        failed.append({"url": url, "error": "crawl_failed"})
                        continue

                    if not getattr(crawl_result, "success", False):
                        failed.append(
                            {
                                "url": url,
                                "error": getattr(crawl_result, "error_message", "crawl_failed")
                                or "crawl_failed",
                            }
                        )
                        continue

                    body = render_crawl_body(
                        crawl_result,
                        preferred_format,
                        include_images=request.include_images,
                        include_links=request.include_links,
                    )
                    images = (
                        extract_images(getattr(crawl_result, "media", {}))
                        if request.include_images
                        else []
                    )
                    favicon = guess_favicon(crawl_result) if request.include_favicon else None
                    title = resolve_title(crawl_result)
                    language = detect_language(crawl_result)
                    metadata = serialize_metadata(crawl_result)

                    extract_result = ExtractResult(
                        url=url,
                        title=title,
                        language=language,
                        raw_content=body,
                        images=images,
                        favicon=favicon,
                        metadata=metadata or None,
                    )
                    results.append(extract_result)

        total_time = time.time() - start_time
        response = ExtractResponse(
            request_id=request_id,
            response_time=total_time,
            results=results,
            failed_results=failed,
        )

        return response.model_dump()
