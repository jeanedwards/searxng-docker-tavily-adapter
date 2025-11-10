"""
Tavily-compatible client for SearXNG
Provides same interface as tavily-python package but uses SearXNG backend
"""
import asyncio
import logging
import time
import uuid
from copy import deepcopy
from typing import Any

import aiohttp
from bs4 import BeautifulSoup
from cachetools import TTLCache
from pydantic import BaseModel

from .config_loader import config


class TavilyResult(BaseModel):
    url: str
    title: str
    content: str
    score: float
    raw_content: str | None = None


class TavilyResponse(BaseModel):
    query: str
    follow_up_questions: list[str] | None = None
    answer: str | None = None
    images: list[str] = []
    results: list[TavilyResult]
    response_time: float
    request_id: str


logger = logging.getLogger(__name__)


class TavilyClient:
    def __init__(self, api_key: str = "", searxng_url: str | None = None):
        self.api_key = api_key  # Stored for API compatibility but never used
        self.searxng_url = (searxng_url or config.searxng_url).rstrip('/')
        # In-memory cache keeps hot search responses for a short time window.
        # TTLCache is used because it is a lightweight and popular Python solution.
        # The cache reduces duplicate calls to SearXNG while keeping memory bounded.
        self._search_cache: TTLCache = TTLCache(
            maxsize=config.search_cache_max_entries,
            ttl=config.search_cache_ttl,
        )
        # Lazy-initialized asyncio lock protects the cache in concurrent scenarios.
        # We create it lazily to avoid touching the event loop during __init__.
        self._cache_lock: asyncio.Lock | None = None
    
    async def _fetch_raw_content(self, session: aiohttp.ClientSession, url: str) -> str | None:
        """Scrape the page and return the first 2500 characters of text."""
        try:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=config.scraper_timeout),
                headers={'User-Agent': config.scraper_user_agent}
            ) as response:
                if response.status != 200:
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Remove layout and script-heavy nodes for cleaner text
                for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                    tag.decompose()
                
                # Extract text content
                text = soup.get_text(separator=' ', strip=True)
                
                # Trim to configured maximum length
                if len(text) > config.scraper_max_length:
                    text = text[:config.scraper_max_length] + "..."
                
                return text
        except Exception:
            return None
        
    def search(
        self,
        query: str,
        max_results: int = 10,
        include_raw_content: bool = False,
    ) -> dict[str, Any]:
        """
        Search using SearXNG with Tavily-compatible interface
        """
        return asyncio.run(self._async_search(
            query=query,
            max_results=max_results,
            include_raw_content=include_raw_content,
        ))
    
    async def _async_search(
        self,
        query: str,
        max_results: int = 10,
        include_raw_content: bool = False,
    ) -> dict[str, Any]:
        # Cache key keeps query parameters compact and hashable.
        cache_key = (query, max_results, include_raw_content)
        cache_lock = self._ensure_cache_lock()
        # We copy cached payloads before returning them so callers cannot modify
        # the shared cached value by mistake.
        async with cache_lock:
            cached_payload = self._search_cache.get(cache_key)
        if cached_payload is not None:
            logger.debug("Serving search response from cache for query=%s", query)
            return deepcopy(cached_payload)

        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        # Build SearXNG request payload
        searxng_params = {
            "q": query,
            "format": "json",
            "categories": "general",
            "engines": "google,duckduckgo,brave",  # Bing removed for stability
            "pageno": 1,
            "language": "auto",
            "safesearch": 1,
        }
        
# Domain filtering removed to keep the API surface minimal
        
        # Extra headers help SearXNG bypass rate limiting and blocking
        headers = {
            'X-Forwarded-For': '127.0.0.1',
            'X-Real-IP': '127.0.0.1',
            'User-Agent': 'Mozilla/5.0 (compatible; TavilyBot/1.0)',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.searxng_url}/search",
                    data=searxng_params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    searxng_data = await response.json()
            except Exception as e:
                # Return an empty result set on failure
                return TavilyResponse(
                    query=query,
                    results=[],
                    response_time=time.time() - start_time,
                    request_id=request_id,
                ).model_dump()
        
        # Convert SearXNG payload into Tavily-format results
        results = []
        searxng_results = searxng_data.get("results", [])
        
        # Scrape additional raw content when requested
        raw_contents = {}
        if include_raw_content and searxng_results:
            urls_to_scrape = [r["url"] for r in searxng_results[:max_results] if r.get("url")]
            
            async with aiohttp.ClientSession() as scrape_session:
                tasks = [self._fetch_raw_content(scrape_session, url) for url in urls_to_scrape]
                page_contents = await asyncio.gather(*tasks, return_exceptions=True)
                
                for url, content in zip(urls_to_scrape, page_contents):
                    if isinstance(content, str) and content:
                        raw_contents[url] = content
        
        for i, result in enumerate(searxng_results[:max_results]):
            if not result.get("url"):
                continue
                
            raw_content = None
            if include_raw_content:
                raw_content = raw_contents.get(result["url"])
                
            tavily_result = TavilyResult(
                url=result["url"],
                title=result.get("title", ""),
                content=result.get("content", ""),
                score=0.9 - (i * 0.05),  # Simple heuristic score placeholder
                raw_content=raw_content
            )
            results.append(tavily_result)
        
        response_time = time.time() - start_time
        
        fresh_payload = TavilyResponse(
            query=query,
            follow_up_questions=None,
            answer=None,
            images=[],
            results=results,
            response_time=response_time,
            request_id=request_id,
        ).model_dump()

        # Cache the freshly computed payload. We store a deep copy
        # so future reads return independent dictionaries.
        async with cache_lock:
            self._search_cache[cache_key] = deepcopy(fresh_payload)

        return fresh_payload

    def _ensure_cache_lock(self) -> asyncio.Lock:
        """
        Provide an asyncio.Lock bound to the current loop.

        The lock is created lazily the first time we need it, ensuring
        we only touch asyncio primitives when a loop is already running.
        """
        if self._cache_lock is None:
            # Lock is attached to the running loop during creation.
            self._cache_lock = asyncio.Lock()
        return self._cache_lock
