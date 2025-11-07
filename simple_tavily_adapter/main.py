"""
FastAPI server that provides Tavily-compatible API using SearXNG backend
"""
import asyncio
import logging
import re
import time
import uuid
from typing import Any, Literal
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from tavily_client import TavilyResponse, TavilyResult
from config_loader import config

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SearXNG Tavily Adapter", version="1.0.0")


class SearchRequest(BaseModel):
    query: str
    max_results: int = 10
    include_raw_content: bool = False


class ExtractRequest(BaseModel):
    urls: list[str] | str
    include_images: bool = False
    include_favicon: bool = False
    extract_depth: Literal["basic", "advanced"] = "basic"
    format: Literal["markdown", "text"] | None = None
    timeout: float | None = None


class ExtractResult(BaseModel):
    url: str
    title: str | None = None
    language: str | None = None
    raw_content: str | None = None
    images: list[dict[str, Any]] = Field(default_factory=list)
    favicon: str | None = None
    metadata: dict[str, Any] | None = None


class ExtractResponse(BaseModel):
    request_id: str
    response_time: float
    results: list[ExtractResult] = Field(default_factory=list)
    failed_results: list[dict[str, str]] = Field(default_factory=list)


async def fetch_raw_content(session: aiohttp.ClientSession, url: str) -> str | None:
    """Скрапит страницу и возвращает первые 2500 символов текста"""
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
            
            # Удаляем ненужное
            for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                tag.decompose()
            
            # Берем текст
            text = soup.get_text(separator=' ', strip=True)
            
            # Обрезаем до настроенного размера
            if len(text) > config.scraper_max_length:
                text = text[:config.scraper_max_length] + "..."
            
            return text
    except Exception:
        return None


def _markdown_to_text(markdown: str) -> str:
    """Convert markdown to a compact plaintext representation"""
    if not markdown:
        return ""
    text = re.sub(r"```[\s\S]*?```", " ", markdown)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"!\[.*?\]\((.*?)\)", " ", text)
    text = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", text)
    text = re.sub(r"[#>*_]+", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def _coerce_url_list(urls: list[str] | str) -> list[str]:
    """Normalize incoming urls payload to a list of strings"""
    if isinstance(urls, str):
        candidate_urls = [urls]
    else:
        candidate_urls = urls
    normalized = []
    for value in candidate_urls:
        if isinstance(value, str):
            trimmed = value.strip()
            if trimmed:
                normalized.append(trimmed)
    return normalized


def _safe_markdown(markdown_obj: Any) -> str | None:
    if not markdown_obj:
        return None
    if isinstance(markdown_obj, str):
        stripped = markdown_obj.strip()
        return stripped or None
    raw_markdown = getattr(markdown_obj, "raw_markdown", None)
    if raw_markdown:
        stripped = raw_markdown.strip()
        if stripped:
            return stripped
    fit_markdown = getattr(markdown_obj, "fit_markdown", None)
    if fit_markdown:
        stripped = fit_markdown.strip()
        if stripped:
            return stripped
    return None


def _render_crawl_body(result: Any, preferred_format: str) -> str | None:
    markdown_body = _safe_markdown(getattr(result, "markdown", None))
    if not markdown_body:
        cleaned_html = getattr(result, "cleaned_html", None) or getattr(result, "html", None)
        if cleaned_html:
            soup = BeautifulSoup(cleaned_html, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)
            markdown_body = text or None
    if not markdown_body:
        return None
    if preferred_format == "text":
        return _markdown_to_text(markdown_body)
    return markdown_body


def _extract_images(media_payload: Any) -> list[dict[str, Any]]:
    if not isinstance(media_payload, dict):
        return []
    images_payload = media_payload.get("images") or []
    images: list[dict[str, Any]] = []
    for item in images_payload:
        if not isinstance(item, dict):
            continue
        src = item.get("src") or item.get("url")
        if not src:
            continue
        images.append({
            "url": src,
            "description": item.get("desc") or item.get("alt"),
            "score": item.get("score"),
        })
    return images


def _guess_favicon(result: Any) -> str | None:
    metadata = getattr(result, "metadata", None)
    if isinstance(metadata, dict):
        favicon = metadata.get("favicon")
        if isinstance(favicon, str) and favicon:
            return favicon
        icons = metadata.get("icons")
        if isinstance(icons, list):
            for icon in icons:
                if isinstance(icon, dict):
                    href = icon.get("href") or icon.get("url")
                    if href:
                        return urljoin(result.url, href)
    html_source = getattr(result, "cleaned_html", None) or getattr(result, "html", None)
    if not html_source:
        return None
    soup = BeautifulSoup(html_source, 'html.parser')
    for link in soup.find_all("link"):
        rel = link.get("rel") or []
        rel_values = [value.lower() for value in rel if isinstance(value, str)]
        if any("icon" in value for value in rel_values):
            href = link.get("href")
            if href:
                return urljoin(result.url, href)
    return None


def _detect_language(result: Any) -> str | None:
    metadata = getattr(result, "metadata", None)
    if isinstance(metadata, dict):
        lang = metadata.get("language") or metadata.get("lang")
        if isinstance(lang, str) and lang:
            return lang.lower()
    html_source = getattr(result, "cleaned_html", None) or getattr(result, "html", None)
    if not html_source:
        return None
    soup = BeautifulSoup(html_source, 'html.parser')
    html_tag = soup.find("html")
    if html_tag:
        lang_attr = html_tag.get("lang") or html_tag.get("xml:lang")
        if lang_attr:
            return lang_attr.lower()
    return None


def _resolve_title(result: Any) -> str | None:
    metadata = getattr(result, "metadata", None)
    if isinstance(metadata, dict):
        for key in ("title", "og:title"):
            value = metadata.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    html_source = getattr(result, "cleaned_html", None) or getattr(result, "html", None)
    if not html_source:
        return None
    soup = BeautifulSoup(html_source, 'html.parser')
    title_tag = soup.find("title")
    if title_tag and title_tag.text:
        return title_tag.text.strip()
    return None


def _build_run_config(depth: str, timeout_seconds: float) -> CrawlerRunConfig:
    timeout_ms = int(max(timeout_seconds, 3) * 1000)
    is_advanced = depth == "advanced"
    return CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        check_robots_txt=True,
        remove_overlay_elements=True,
        process_iframes=is_advanced,
        word_count_threshold=8 if is_advanced else 12,
        page_timeout=timeout_ms,
        delay_before_return_html=1.0 if is_advanced else 0.0,
    )


def _serialize_metadata(result: Any) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    native_meta = getattr(result, "metadata", None)
    if isinstance(native_meta, dict):
        metadata.update(native_meta)
    if getattr(result, "status_code", None) is not None:
        metadata["status_code"] = result.status_code
    if getattr(result, "response_headers", None):
        headers = getattr(result, "response_headers")
        try:
            metadata["response_headers"] = dict(headers)
        except Exception:
            metadata["response_headers"] = headers
    if getattr(result, "error_message", None):
        metadata["error_message"] = result.error_message
    return metadata


@app.post("/search")
async def search(request: SearchRequest) -> dict[str, Any]:
    """
    Tavily-compatible search endpoint
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    logger.info(f"Search request: {request.query}")
    
    # Формируем запрос к SearXNG
    searxng_params = {
        "q": request.query,
        "format": "json",
        "categories": "general",
        "engines": "google,duckduckgo,brave",  # Убрали Bing
        "pageno": 1,
        "language": "auto",
        "safesearch": 1,
    }
    
# Убрали обработку доменов - не нужно для упрощенного API
    
    # Выполняем запрос к SearXNG
    headers = {
        'X-Forwarded-For': '127.0.0.1',
        'X-Real-IP': '127.0.0.1',
        'User-Agent': 'Mozilla/5.0 (compatible; TavilyBot/1.0)',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{config.searxng_url}/search",
                data=searxng_params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    raise HTTPException(status_code=500, detail="SearXNG request failed")
                searxng_data = await response.json()
        except asyncio.TimeoutError:
            # Modern aiohttp uses asyncio.TimeoutError instead of aiohttp.TimeoutError
            raise HTTPException(status_code=504, detail="SearXNG timeout")
        except aiohttp.ClientError as e:
            # Catch DNS errors, connection errors, etc.
            logger.error(f"SearXNG connection error: {e}")
            raise HTTPException(status_code=503, detail="Cannot connect to search service")
        except Exception as e:
            logger.error(f"SearXNG error: {e}")
            raise HTTPException(status_code=500, detail="Search service unavailable")
    
    # Конвертируем результаты в формат Tavily
    results = []
    searxng_results = searxng_data.get("results", [])
    
    # Если нужен raw_content, скрапим страницы
    raw_contents = {}
    if request.include_raw_content and searxng_results:
        urls_to_scrape = [r["url"] for r in searxng_results[:request.max_results] if r.get("url")]
        
        async with aiohttp.ClientSession() as scrape_session:
            tasks = [fetch_raw_content(scrape_session, url) for url in urls_to_scrape]
            page_contents = await asyncio.gather(*tasks, return_exceptions=True)
            
            for url, content in zip(urls_to_scrape, page_contents):
                if isinstance(content, str) and content:
                    raw_contents[url] = content
    
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
            score=0.9 - (i * 0.05),  # Простая имитация скора
            raw_content=raw_content
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
    
    logger.info(f"Search completed: {len(results)} results in {response_time:.2f}s")
    
    return response.model_dump()


@app.post("/extract")
async def extract(request: ExtractRequest) -> dict[str, Any]:
    """
    Tavily-compatible extract endpoint powered by Crawl4AI
    """
    urls = _coerce_url_list(request.urls)
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
        config.extract_timeout_advanced if request.extract_depth == "advanced"
        else config.extract_timeout_basic
    )

    run_config = _build_run_config(request.extract_depth, per_url_timeout)
    request_id = str(uuid.uuid4())
    start_time = time.time()
    results: list[ExtractResult] = []
    failed: list[dict[str, str]] = []

    async with AsyncWebCrawler() as crawler:
        for url in urls:
            try:
                crawl_future = crawler.arun(url=url, config=run_config)
                crawl_result = await asyncio.wait_for(
                    crawl_future,
                    timeout=per_url_timeout + 2,
                )
            except asyncio.TimeoutError:
                logger.warning("Extract timeout for %s", url)
                failed.append({"url": url, "error": "timeout"})
                continue
            except Exception as exc:
                logger.error("Extract error for %s: %s", url, exc)
                failed.append({"url": url, "error": "crawl_failed"})
                continue

            if not getattr(crawl_result, "success", False):
                failed.append({
                    "url": url,
                    "error": getattr(crawl_result, "error_message", "crawl_failed") or "crawl_failed"
                })
                continue

            body = _render_crawl_body(crawl_result, preferred_format)
            images = _extract_images(getattr(crawl_result, "media", {})) if request.include_images else []
            favicon = _guess_favicon(crawl_result) if request.include_favicon else None
            title = _resolve_title(crawl_result)
            language = _detect_language(crawl_result)
            metadata = _serialize_metadata(crawl_result)

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


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "searxng-tavily-adapter"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.server_host, port=config.server_port)
