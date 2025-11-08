"""
Utility functions for content processing and extraction.

This module contains pure helper functions for processing web content,
including markdown conversion, image extraction, metadata parsing, etc.
All functions are stateless and have no external dependencies.
"""
import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from crawl4ai import CacheMode, CrawlerRunConfig

from .config_loader import config


def build_search_crawl_config() -> CrawlerRunConfig:
    """
    Creates a lightweight CrawlerRunConfig optimized for search result scraping.
    
    Uses fast settings to balance speed and reliability for bulk search results.
    Bypasses cache, checks robots.txt, and minimizes delays.
    
    Returns:
        CrawlerRunConfig: Configuration for fast search scraping
    """
    timeout_ms = int(config.scraper_timeout * 1000)
    return CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        check_robots_txt=True,
        remove_overlay_elements=True,
        process_iframes=False,  # Fast mode: skip iframes
        word_count_threshold=12,  # Basic extraction threshold
        page_timeout=timeout_ms,
        delay_before_return_html=0.0,  # No delay for speed
    )


def markdown_to_text(markdown: str) -> str:
    """
    Convert markdown to a compact plaintext representation.
    
    Removes code blocks, links, images, and markdown formatting
    while preserving the core text content.
    
    Args:
        markdown: Input markdown string
        
    Returns:
        Cleaned plaintext string
    """
    if not markdown:
        return ""
    
    # Remove code blocks
    text = re.sub(r"```[\s\S]*?```", " ", markdown)
    
    # Remove inline code
    text = re.sub(r"`([^`]+)`", r"\1", text)
    
    # Remove images
    text = re.sub(r"!\[.*?\]\((.*?)\)", " ", text)
    
    # Convert links to just their text
    text = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", text)
    
    # Remove markdown formatting characters
    text = re.sub(r"[#>*_]+", " ", text)
    
    # Normalize whitespace
    text = re.sub(r"\s{2,}", " ", text)
    
    return text.strip()


def coerce_url_list(urls: list[str] | str) -> list[str]:
    """
    Normalize incoming URLs payload to a list of strings.
    
    Handles both single URL strings and lists, filtering out
    empty values and trimming whitespace.
    
    Args:
        urls: Single URL string or list of URL strings
        
    Returns:
        List of normalized URL strings
    """
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


def safe_markdown(markdown_obj: Any) -> str | None:
    """
    Safely extract markdown string from various object types.
    
    Handles Crawl4AI result objects that may have markdown in different
    attributes (raw_markdown, fit_markdown) or as direct strings.
    
    Args:
        markdown_obj: Object that may contain markdown content
        
    Returns:
        Extracted markdown string or None if not found
    """
    if not markdown_obj:
        return None
    
    # Direct string case
    if isinstance(markdown_obj, str):
        stripped = markdown_obj.strip()
        return stripped or None
    
    # Try raw_markdown attribute
    raw_markdown = getattr(markdown_obj, "raw_markdown", None)
    if raw_markdown:
        stripped = raw_markdown.strip()
        if stripped:
            return stripped
    
    # Try fit_markdown attribute
    fit_markdown = getattr(markdown_obj, "fit_markdown", None)
    if fit_markdown:
        stripped = fit_markdown.strip()
        if stripped:
            return stripped
    
    return None


def render_crawl_body(result: Any, preferred_format: str) -> str | None:
    """
    Render crawl result body in the requested format.
    
    Extracts content from Crawl4AI result, preferring markdown but
    falling back to cleaned HTML. Converts to text if requested.
    
    Args:
        result: Crawl4AI result object
        preferred_format: "markdown" or "text"
        
    Returns:
        Rendered content string or None if no content available
    """
    # Try to get markdown first
    markdown_body = safe_markdown(getattr(result, "markdown", None))
    
    # Fallback to HTML parsing
    if not markdown_body:
        cleaned_html = getattr(result, "cleaned_html", None) or getattr(result, "html", None)
        if cleaned_html:
            soup = BeautifulSoup(cleaned_html, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)
            markdown_body = text or None
    
    if not markdown_body:
        return None
    
    # Convert to text format if requested
    if preferred_format == "text":
        return markdown_to_text(markdown_body)
    
    return markdown_body


def extract_images(media_payload: Any) -> list[dict[str, Any]]:
    """
    Extract image information from Crawl4AI media payload.
    
    Parses the media dictionary and extracts image URLs with
    descriptions and scores.
    
    Args:
        media_payload: Media dictionary from Crawl4AI result
        
    Returns:
        List of image dictionaries with url, description, and score
    """
    if not isinstance(media_payload, dict):
        return []
    
    images_payload = media_payload.get("images") or []
    images: list[dict[str, Any]] = []
    
    for item in images_payload:
        if not isinstance(item, dict):
            continue
        
        # Get image URL from various possible keys
        src = item.get("src") or item.get("url")
        if not src:
            continue
        
        images.append({
            "url": src,
            "description": item.get("desc") or item.get("alt"),
            "score": item.get("score"),
        })
    
    return images


def guess_favicon(result: Any) -> str | None:
    """
    Attempt to extract favicon URL from crawl result.
    
    Checks metadata first, then parses HTML for link tags with
    rel="icon" attributes. Resolves relative URLs to absolute.
    
    Args:
        result: Crawl4AI result object
        
    Returns:
        Absolute favicon URL or None if not found
    """
    # Check metadata first
    metadata = getattr(result, "metadata", None)
    if isinstance(metadata, dict):
        favicon = metadata.get("favicon")
        if isinstance(favicon, str) and favicon:
            return favicon
        
        # Check icons array
        icons = metadata.get("icons")
        if isinstance(icons, list):
            for icon in icons:
                if isinstance(icon, dict):
                    href = icon.get("href") or icon.get("url")
                    if href:
                        return urljoin(result.url, href)
    
    # Parse HTML for link tags
    html_source = getattr(result, "cleaned_html", None) or getattr(result, "html", None)
    if not html_source:
        return None
    
    soup = BeautifulSoup(html_source, 'html.parser')
    for link in soup.find_all("link"):
        rel = link.get("rel") or []
        rel_values = [value.lower() for value in rel if isinstance(value, str)]
        
        # Look for icon-related rel values
        if any("icon" in value for value in rel_values):
            href = link.get("href")
            if href:
                return urljoin(result.url, href)
    
    return None


def detect_language(result: Any) -> str | None:
    """
    Detect page language from metadata or HTML attributes.
    
    Checks metadata first, then HTML lang attributes.
    Returns lowercase language codes.
    
    Args:
        result: Crawl4AI result object
        
    Returns:
        Language code (lowercase) or None if not detected
    """
    # Check metadata
    metadata = getattr(result, "metadata", None)
    if isinstance(metadata, dict):
        lang = metadata.get("language") or metadata.get("lang")
        if isinstance(lang, str) and lang:
            return lang.lower()
    
    # Parse HTML for lang attribute
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


def resolve_title(result: Any) -> str | None:
    """
    Extract page title from metadata or HTML.
    
    Checks metadata (including OpenGraph title) first,
    then falls back to parsing HTML title tag.
    
    Args:
        result: Crawl4AI result object
        
    Returns:
        Page title string or None if not found
    """
    # Check metadata sources
    metadata = getattr(result, "metadata", None)
    if isinstance(metadata, dict):
        for key in ("title", "og:title"):
            value = metadata.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    
    # Parse HTML for title tag
    html_source = getattr(result, "cleaned_html", None) or getattr(result, "html", None)
    if not html_source:
        return None
    
    soup = BeautifulSoup(html_source, 'html.parser')
    title_tag = soup.find("title")
    if title_tag and title_tag.text:
        return title_tag.text.strip()
    
    return None


def build_run_config(depth: str, timeout_seconds: float) -> CrawlerRunConfig:
    """
    Build CrawlerRunConfig based on extraction depth.
    
    Creates optimized configuration for either "basic" (fast) or
    "advanced" (thorough) extraction modes.
    
    Args:
        depth: "basic" or "advanced"
        timeout_seconds: Timeout in seconds (minimum 3s)
        
    Returns:
        CrawlerRunConfig: Configuration tuned for requested depth
    """
    timeout_ms = int(max(timeout_seconds, 3) * 1000)
    is_advanced = depth == "advanced"
    
    return CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        check_robots_txt=True,
        remove_overlay_elements=True,
        process_iframes=is_advanced,  # Only process iframes in advanced mode
        word_count_threshold=8 if is_advanced else 12,
        page_timeout=timeout_ms,
        delay_before_return_html=1.0 if is_advanced else 0.0,  # Wait for JS in advanced mode
    )


def serialize_metadata(result: Any) -> dict[str, Any]:
    """
    Serialize crawl result metadata to a dictionary.
    
    Extracts metadata, status codes, response headers, and error
    messages from Crawl4AI result objects.
    
    Args:
        result: Crawl4AI result object
        
    Returns:
        Dictionary of metadata fields
    """
    metadata: dict[str, Any] = {}
    
    # Copy native metadata
    native_meta = getattr(result, "metadata", None)
    if isinstance(native_meta, dict):
        metadata.update(native_meta)
    
    # Add status code
    if getattr(result, "status_code", None) is not None:
        metadata["status_code"] = result.status_code
    
    # Add response headers
    if getattr(result, "response_headers", None):
        headers = getattr(result, "response_headers")
        try:
            metadata["response_headers"] = dict(headers)
        except Exception:
            metadata["response_headers"] = headers
    
    # Add error message if present
    if getattr(result, "error_message", None):
        metadata["error_message"] = result.error_message
    
    return metadata

