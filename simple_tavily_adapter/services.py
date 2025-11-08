"""
Business logic services for search and extract operations.

This module contains service classes that implement core functionality:
- SearchService: Handles search queries via SearXNG with optional content scraping
- ExtractService: Extracts content from URLs using Crawl4AI

Services are designed to be independent of HTTP concerns and can be
reused in different contexts (API, CLI, tests).
"""
import asyncio
import logging
import time
import uuid
from typing import Any

import aiohttp
from crawl4ai import AsyncWebCrawler
from fastapi import HTTPException

from .config_loader import config
from .models import (
    SearchRequest,
    ExtractRequest,
    ExtractResult,
    ExtractResponse,
    TavilyResponse,
    TavilyResult,
)
from .utils import (
    build_search_crawl_config,
    build_run_config,
    coerce_url_list,
    detect_language,
    extract_images,
    guess_favicon,
    render_crawl_body,
    resolve_title,
    safe_markdown,
    serialize_metadata,
)


class SearchService:
    """
    Service for performing searches via SearXNG backend.
    
    Handles querying SearXNG, optional content scraping with Crawl4AI,
    and transformation of results to Tavily-compatible format.
    """
    
    def __init__(self, logger: logging.Logger | None = None):
        """
        Initialize search service.
        
        Args:
            logger: Logger instance (creates new one if not provided)
        """
        self.logger = logger or logging.getLogger(__name__)
    
    async def _fetch_raw_content_crawl4ai(
        self,
        crawler: AsyncWebCrawler,
        url: str,
        config_obj: Any,
    ) -> tuple[str | None, str | None]:
        """
        Scrape a page using Crawl4AI and return markdown content.
        
        Handles timeouts and errors gracefully, returning either content
        or an error description.
        
        Args:
            crawler: AsyncWebCrawler instance
            url: URL to scrape
            config_obj: CrawlerRunConfig for the crawl
            
        Returns:
            Tuple of (markdown_content, error_message)
            - On success: (markdown_string, None)
            - On failure: (None, error_description)
        """
        try:
            # Execute crawl with timeout
            crawl_future = crawler.arun(url=url, config=config_obj)
            crawl_result = await asyncio.wait_for(
                crawl_future,
                timeout=config.scraper_timeout + 2,
            )
        except asyncio.TimeoutError:
            return None, "timeout"
        except Exception as exc:
            self.logger.warning(f"Crawl error for {url}: {exc}")
            return None, "crawl_failed"
        
        # Check if crawl was successful
        if not getattr(crawl_result, "success", False):
            error_msg = getattr(crawl_result, "error_message", "unknown_error") or "unknown_error"
            return None, error_msg
        
        # Extract markdown content
        markdown = safe_markdown(getattr(crawl_result, "markdown", None))
        if not markdown:
            return None, "no_content"
        
        # Truncate to configured max length
        if len(markdown) > config.scraper_max_length:
            markdown = markdown[:config.scraper_max_length] + "..."
        
        return markdown, None
    
    async def search(self, request: SearchRequest) -> dict[str, Any]:
        """
        Execute search query via SearXNG and optionally scrape results.
        
        Main search workflow:
        1. Query SearXNG with configured engines
        2. If include_raw_content is True, scrape pages with Crawl4AI
        3. Transform results to Tavily-compatible format
        
        Args:
            request: SearchRequest with query and options
            
        Returns:
            Dictionary containing TavilyResponse data
            
        Raises:
            HTTPException: On SearXNG connection or timeout errors
        """
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        self.logger.info(f"Search request: {request.query}")
        
        # Build SearXNG query parameters
        searxng_params = {
            "q": request.query,
            "format": "json",
            "categories": "general",
            "engines": "google,duckduckgo,brave",
            "pageno": 1,
            "language": "auto",
            "safesearch": 1,
        }
        
        # Set headers to bypass SearXNG rate limiting
        headers = {
            'X-Forwarded-For': '127.0.0.1',
            'X-Real-IP': '127.0.0.1',
            'User-Agent': 'Mozilla/5.0 (compatible; TavilyBot/1.0)',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        # Execute SearXNG query
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{config.searxng_url}/search",
                    data=searxng_params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        self.logger.error(f"SearXNG returned {response.status}: {error_text[:500]}")
                        raise HTTPException(
                            status_code=500,
                            detail=f"SearXNG request failed with status {response.status}"
                        )
                    searxng_data = await response.json()
            except asyncio.TimeoutError:
                raise HTTPException(status_code=504, detail="SearXNG timeout")
            except aiohttp.ClientError as e:
                self.logger.error(f"SearXNG connection error: {e}")
                raise HTTPException(status_code=503, detail="Cannot connect to search service")
            except Exception as e:
                self.logger.error(f"SearXNG error: {e}")
                raise HTTPException(status_code=500, detail="Search service unavailable")
        
        # Parse search results
        results = []
        searxng_results = searxng_data.get("results", [])
        
        # Scrape raw content if requested
        raw_contents = {}
        scraping_stats = {"total": 0, "success": 0, "failed": 0, "errors": {}}
        
        if request.include_raw_content and searxng_results:
            urls_to_scrape = [r["url"] for r in searxng_results[:request.max_results] if r.get("url")]
            scraping_stats["total"] = len(urls_to_scrape)
            
            # Initialize Crawl4AI crawler and config
            crawl_config = build_search_crawl_config()
            
            async with AsyncWebCrawler() as crawler:
                # Create parallel crawl tasks for all URLs
                tasks = [
                    self._fetch_raw_content_crawl4ai(crawler, url, crawl_config)
                    for url in urls_to_scrape
                ]
                crawl_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results and collect statistics
                for url, crawl_result in zip(urls_to_scrape, crawl_results):
                    if isinstance(crawl_result, Exception):
                        # Handle unexpected exceptions
                        self.logger.warning(f"Unexpected error scraping {url}: {crawl_result}")
                        scraping_stats["failed"] += 1
                        error_type = type(crawl_result).__name__
                        errors_dict = scraping_stats["errors"]
                        if isinstance(errors_dict, dict):
                            errors_dict[error_type] = errors_dict.get(error_type, 0) + 1
                        continue
                    
                    content, error = crawl_result
                    if content:
                        # Success: store markdown content
                        raw_contents[url] = content
                        scraping_stats["success"] += 1
                    else:
                        # Failed: log the error reason
                        scraping_stats["failed"] += 1
                        error_type = error or "unknown"
                        errors_dict = scraping_stats["errors"]
                        if isinstance(errors_dict, dict):
                            errors_dict[error_type] = errors_dict.get(error_type, 0) + 1
                        self.logger.debug(f"Failed to scrape {url}: {error_type}")
            
            # Log scraping statistics for observability
            self.logger.info(
                f"Raw content scraping: {scraping_stats['success']}/{scraping_stats['total']} successful, "
                f"{scraping_stats['failed']} failed. Errors: {dict(scraping_stats['errors'])}"
            )
        
        # Transform SearXNG results to Tavily format
        for i, result in enumerate(searxng_results[:request.max_results]):
            if not result.get("url"):
                continue
            
            raw_content = None
            if request.include_raw_content:
                raw_content = raw_contents.get(result["url"])
            
            tavily_result = TavilyResult(
                url=result["url"],
                title=result.get("title", ""),
                content=result.get("content", ""),
                score=0.9 - (i * 0.05),  # Simple score simulation
                raw_content=raw_content
            )
            results.append(tavily_result)
        
        response_time = time.time() - start_time
        
        # Build Tavily-compatible response
        response = TavilyResponse(
            query=request.query,
            follow_up_questions=None,
            answer=None,
            images=[],
            results=results,
            response_time=response_time,
            request_id=request_id,
        )
        
        self.logger.info(f"Search completed: {len(results)} results in {response_time:.2f}s")
        
        return response.model_dump()


class ExtractService:
    """
    Service for extracting content from URLs using Crawl4AI.
    
    Handles parallel extraction of multiple URLs with configurable
    depth, format, and metadata extraction options.
    """
    
    def __init__(self, logger: logging.Logger | None = None):
        """
        Initialize extract service.
        
        Args:
            logger: Logger instance (creates new one if not provided)
        """
        self.logger = logger or logging.getLogger(__name__)
    
    async def extract(self, request: ExtractRequest) -> dict[str, Any]:
        """
        Extract content from one or more URLs using Crawl4AI.
        
        Main extraction workflow:
        1. Normalize and validate URL list
        2. Build crawler configuration based on depth and timeout
        3. Crawl URLs in sequence (respecting robots.txt)
        4. Extract content, images, favicon, metadata as requested
        5. Return results with failed URLs separately
        
        Args:
            request: ExtractRequest with URLs and extraction options
            
        Returns:
            Dictionary containing ExtractResponse data
            
        Raises:
            HTTPException: On invalid request parameters
        """
        # Normalize URL list
        urls = coerce_url_list(request.urls)
        if not urls:
            raise HTTPException(status_code=400, detail="At least one URL is required")
        if len(urls) > config.extract_max_urls:
            raise HTTPException(
                status_code=400,
                detail=f"Too many URLs. Max allowed: {config.extract_max_urls}",
            )
        
        # Determine output format
        preferred_format = (request.format or config.extract_default_format).lower()
        if preferred_format not in {"markdown", "text"}:
            raise HTTPException(status_code=400, detail="format must be 'markdown' or 'text'")
        
        # Determine timeout based on depth
        per_url_timeout = request.timeout or (
            config.extract_timeout_advanced if request.extract_depth == "advanced"
            else config.extract_timeout_basic
        )
        
        # Build crawler configuration
        run_config = build_run_config(request.extract_depth, per_url_timeout)
        request_id = str(uuid.uuid4())
        start_time = time.time()
        results: list[ExtractResult] = []
        failed: list[dict[str, str]] = []
        
        # Crawl each URL
        async with AsyncWebCrawler() as crawler:
            for url in urls:
                try:
                    crawl_future = crawler.arun(url=url, config=run_config)
                    crawl_result = await asyncio.wait_for(
                        crawl_future,
                        timeout=per_url_timeout + 2,
                    )
                except asyncio.TimeoutError:
                    self.logger.warning("Extract timeout for %s", url)
                    failed.append({"url": url, "error": "timeout"})
                    continue
                except Exception as exc:
                    self.logger.error("Extract error for %s: %s", url, exc)
                    failed.append({"url": url, "error": "crawl_failed"})
                    continue
                
                # Check if crawl succeeded
                if not getattr(crawl_result, "success", False):
                    failed.append({
                        "url": url,
                        "error": getattr(crawl_result, "error_message", "crawl_failed") or "crawl_failed"
                    })
                    continue
                
                # Extract requested data
                body = render_crawl_body(crawl_result, preferred_format)
                images = extract_images(getattr(crawl_result, "media", {})) if request.include_images else []
                favicon = guess_favicon(crawl_result) if request.include_favicon else None
                title = resolve_title(crawl_result)
                language = detect_language(crawl_result)
                metadata = serialize_metadata(crawl_result)
                
                # Build result object
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
        
        # Build response
        total_time = time.time() - start_time
        response = ExtractResponse(
            request_id=request_id,
            response_time=total_time,
            results=results,
            failed_results=failed,
        )
        
        return response.model_dump()

