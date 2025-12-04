"""
Utility functions for content processing and extraction.

This module contains pure helper functions for processing web content,
including markdown conversion, image extraction, metadata parsing, PDF extraction.
All functions are stateless and have no external dependencies.
"""

import io
import re
from typing import Any
from urllib.parse import urljoin, urlparse

import aiohttp
import fitz  # PyMuPDF for PDF text extraction
from bs4 import BeautifulSoup
from crawl4ai import BrowserConfig, CacheMode, CrawlerRunConfig
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

from .config_loader import config

# HTML tags to exclude from content extraction (navigation, headers, footers, etc.)
EXCLUDED_TAGS = [
    "nav",
    "header",
    "footer",
    "aside",
    "menu",
    "sidebar",
    "advertisement",
    "noscript",
    "script",
    "style",
    "form",
    "button",
    "iframe",
    "svg",
    "canvas",
    "video",
    "audio",
    "figure",  # Often contains decorative images
    "figcaption",
]

# Common image file extensions (including exotic formats)
IMAGE_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".bmp",
    ".tiff",
    ".tif",
    ".avif",
    ".heic",
    ".heif",
    ".jfif",
    ".pjpeg",
    ".pjp",
)

# Regex patterns to remove common noise from markdown output
# These patterns match common UI elements, social links, cookie notices, etc.
NOISE_PATTERNS = [
    # Social media sharing buttons and links
    r"(?m)^\s*\[?(Share|Tweet|Pin|Email|Print|Copy|Like|Follow|Subscribe)\]?\s*$",
    r"(?m)^\s*\[?(Facebook|Twitter|LinkedIn|Instagram|YouTube|TikTok|Pinterest)\]?\s*$",
    # Cookie and privacy notices
    r"(?m)^\s*\[?(Accept|Reject|Cookie|Privacy|GDPR|Consent)\s*(All|Cookies|Settings|Policy)?\]?\s*$",
    # Navigation breadcrumbs and pagination
    r"(?m)^\s*\[?(Home|Back|Next|Previous|Page|›|»|«|‹)\]?\s*$",
    r"(?m)^\s*\d+\s*$",  # Standalone page numbers
    # Login/signup prompts
    r"(?m)^\s*\[?(Sign\s*(In|Up|Out)|Log\s*(In|Out)|Register|Login|Logout)\]?\s*$",
    # Empty or near-empty lines with just symbols
    r"(?m)^\s*[\|\-\*\_\#\>\•\·\–\—]+\s*$",
    # Read more / continue reading links
    r"(?m)^\s*\[?(Read\s*More|Continue\s*Reading|See\s*More|View\s*More|Load\s*More)\]?\s*$",
    # Copyright and legal text (usually at bottom)
    r"(?m)^\s*©.*\d{4}.*$",
    r"(?m)^\s*All\s*Rights\s*Reserved.*$",
    # Skip to content links
    r"(?m)^\s*\[?Skip\s*(to)?\s*(Main)?\s*Content\]?\s*$",
]


def build_browser_config() -> BrowserConfig:
    """
    Build BrowserConfig with cookies and stealth settings from configuration.

    Reads browser settings from config.yaml including:
    - headless mode
    - persistent context for session cookies
    - custom cookies for authenticated access
    - extra HTTP headers

    Also enables anti-bot detection features:
    - enable_stealth: Uses playwright-stealth to modify browser fingerprints
    - extra_args: Chromium flags to avoid automation detection
    - ignore_https_errors: Handles HTTP/2 protocol errors on protected sites

    Returns:
        BrowserConfig: Configuration for AsyncWebCrawler browser
    """
    # Extra browser args to avoid bot detection
    # These flags help bypass automation detection on protected sites
    stealth_args = [
        "--disable-blink-features=AutomationControlled",  # Hide automation flag
        "--disable-dev-shm-usage",  # Avoid shared memory issues in containers
        "--no-sandbox",  # Required for some containerized environments
        "--disable-web-security",  # Help with CORS/protocol issues
        "--disable-features=VizDisplayCompositor",  # Reduce fingerprinting
    ]

    # Build browser config with cookies and stealth settings
    browser_config = BrowserConfig(
        headless=config.browser_headless,
        verbose=False,
        # Use a realistic user agent
        user_agent=config.scraper_user_agent,
        # Extra headers from config
        headers=config.browser_extra_headers if config.browser_extra_headers else None,
        # Enable stealth mode to bypass basic bot detection
        enable_stealth=True,
        # Extra Chromium args for anti-detection
        extra_args=stealth_args,
        # Ignore HTTPS/TLS errors (helps with ERR_HTTP2_PROTOCOL_ERROR)
        ignore_https_errors=True,
    )

    # Add cookies if configured
    if config.browser_cookies:
        browser_config.cookies = config.browser_cookies

    # Enable persistent context if configured (maintains cookies across requests)
    if config.browser_use_persistent_context:
        browser_config.use_persistent_context = True

    return browser_config


def build_search_crawl_config() -> CrawlerRunConfig:
    """
    Creates a lightweight CrawlerRunConfig optimized for search result scraping.

    Uses balanced settings for speed and content quality. Excludes navigation
    elements and applies aggressive pruning filter to focus on main content.

    Also enables anti-bot detection features for protected sites.

    Returns:
        CrawlerRunConfig: Configuration for quality search scraping
    """
    timeout_ms = int(config.scraper_timeout * 1000)

    # Content filter to remove low-relevance sections (sidebars, menus, etc.)
    # Higher threshold = more aggressive filtering (0.0-1.0 scale)
    prune_filter = PruningContentFilter(
        threshold=0.55,  # Aggressive threshold to reduce noise
        threshold_type="fixed",
        min_word_threshold=15,  # Require more words per block to retain
    )

    # Markdown generator with content filtering
    md_generator = DefaultMarkdownGenerator(content_filter=prune_filter)

    return CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        check_robots_txt=False,  # Disabled to allow extraction from all sites
        remove_overlay_elements=True,
        process_iframes=False,  # Fast mode: skip iframes
        excluded_tags=EXCLUDED_TAGS,  # Remove nav, header, footer, aside, etc.
        word_count_threshold=12,  # Higher threshold filters out short noise blocks
        page_timeout=timeout_ms,
        delay_before_return_html=0.3,  # Small delay for dynamic content to load
        markdown_generator=md_generator,
        # Anti-bot detection features to bypass protected sites
        magic=True,  # Auto-handle common bot detection patterns
        simulate_user=True,  # Simulate human-like behavior
        override_navigator=True,  # Spoof navigator properties
    )


def strip_image_links(markdown: str) -> str:
    """
    Remove all image references from markdown content.

    Strips markdown image syntax ![alt](url), standalone image URLs,
    and HTML img tags. Supports all common image formats including
    exotic ones like webp, avif, heic.

    Args:
        markdown: Markdown string with potential image links

    Returns:
        Markdown with all image references removed
    """
    if not markdown:
        return ""

    result = markdown

    # Remove markdown image syntax: ![alt text](url)
    result = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", result)

    # Remove HTML img tags: <img ... />
    result = re.sub(r"<img[^>]*>", "", result, flags=re.IGNORECASE)

    # Build regex pattern for image extensions (case insensitive)
    # Matches URLs ending with image extensions
    ext_pattern = "|".join(re.escape(ext) for ext in IMAGE_EXTENSIONS)

    # Remove standalone image URLs (lines that are just image URLs)
    # Matches http(s) URLs ending with image extensions
    result = re.sub(
        rf"(?m)^\s*https?://[^\s]+({ext_pattern})(\?[^\s]*)?\s*$",
        "",
        result,
        flags=re.IGNORECASE,
    )

    # Remove image URLs in markdown links: [text](image_url)
    # Only removes links where the URL points to an image file
    result = re.sub(
        rf"\[[^\]]*\]\(([^)]+({ext_pattern})(\?[^)]*)?)\)",
        "",
        result,
        flags=re.IGNORECASE,
    )

    # Remove inline image URLs within text
    # Be careful not to break valid text - only remove URLs that look like images
    result = re.sub(
        rf"https?://[^\s<>\"]+({ext_pattern})(\?[^\s<>\"]*)?",
        "",
        result,
        flags=re.IGNORECASE,
    )

    return result


def strip_links(markdown: str) -> str:
    """
    Remove all links from markdown content, preserving link text.

    Converts markdown links to plain text, removes standalone URLs,
    and strips HTML anchor tags while keeping their text content.

    Args:
        markdown: Markdown string with potential links

    Returns:
        Markdown with all links removed but text preserved
    """
    if not markdown:
        return ""

    result = markdown

    # Convert markdown links to just their text: [text](url) → text
    result = re.sub(r"\[([^\]]*)\]\([^)]+\)", r"\1", result)

    # Remove HTML anchor tags but keep text: <a href="...">text</a> → text
    result = re.sub(r"<a\s+[^>]*>([^<]*)</a>", r"\1", result, flags=re.IGNORECASE)

    # Remove standalone URLs (lines that are just URLs)
    result = re.sub(r"(?m)^\s*https?://[^\s]+\s*$", "", result)

    # Remove inline URLs (bare URLs in text)
    # This pattern matches URLs that aren't part of markdown syntax
    result = re.sub(r"https?://[^\s<>\")\]]+", "", result)

    # Clean up any leftover empty parentheses or brackets
    result = re.sub(r"\(\s*\)", "", result)
    result = re.sub(r"\[\s*\]", "", result)

    return result


def clean_markdown_noise(markdown: str) -> str:
    """
    Remove common noise patterns from markdown content.

    Applies regex patterns to strip social buttons, cookie notices,
    navigation elements, and other UI noise that often survives
    HTML-to-markdown conversion.

    Args:
        markdown: Raw markdown string

    Returns:
        Cleaned markdown with noise removed
    """
    if not markdown:
        return ""

    result = markdown

    # Apply all noise removal patterns
    for pattern in NOISE_PATTERNS:
        result = re.sub(pattern, "", result, flags=re.IGNORECASE)

    # Remove excessive blank lines (more than 2 consecutive)
    result = re.sub(r"\n{4,}", "\n\n\n", result)

    # Remove lines that are just markdown formatting with no content
    # e.g., "###" or "**" or "---" alone
    result = re.sub(r"(?m)^\s*[#*_\-]{1,6}\s*$", "", result)

    # Clean up leading/trailing whitespace per line and overall
    lines = [line.rstrip() for line in result.split("\n")]
    result = "\n".join(lines).strip()

    return result


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
    Prefers fit_markdown (filtered) over raw_markdown (unfiltered) for better quality.

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

    # PREFER fit_markdown (filtered content) - BETTER QUALITY
    # fit_markdown applies word_count_threshold filtering to remove noise
    fit_markdown = getattr(markdown_obj, "fit_markdown", None)
    if fit_markdown:
        stripped = fit_markdown.strip()
        if stripped:
            return stripped

    # FALLBACK to raw_markdown (unfiltered)
    # raw_markdown contains all converted HTML including navigation, ads, etc.
    raw_markdown = getattr(markdown_obj, "raw_markdown", None)
    if raw_markdown:
        stripped = raw_markdown.strip()
        if stripped:
            return stripped

    return None


def render_crawl_body(
    result: Any,
    preferred_format: str,
    include_images: bool = True,
    include_links: bool = True,
) -> str | None:
    """
    Render crawl result body in the requested format.

    Extracts content from Crawl4AI result, preferring markdown but
    falling back to cleaned HTML. Applies noise reduction and
    converts to text if requested. Optionally strips image and other links.

    Args:
        result: Crawl4AI result object
        preferred_format: "markdown" or "text"
        include_images: If False, strips all image links from output
        include_links: If False, strips all links (preserves text)

    Returns:
        Rendered content string or None if no content available
    """
    # Try to get markdown first
    markdown_body = safe_markdown(getattr(result, "markdown", None))

    # Fallback to HTML parsing
    if not markdown_body:
        cleaned_html = getattr(result, "cleaned_html", None) or getattr(result, "html", None)
        if cleaned_html:
            soup = BeautifulSoup(cleaned_html, "html.parser")
            text = soup.get_text(separator=" ", strip=True)
            markdown_body = text or None

    if not markdown_body:
        return None

    # Apply noise reduction to remove social buttons, cookie notices, etc.
    markdown_body = clean_markdown_noise(markdown_body)

    # Strip image links if not requested (do this before general link stripping)
    if not include_images:
        markdown_body = strip_image_links(markdown_body)

    # Strip all links if not requested (preserves link text)
    if not include_links:
        markdown_body = strip_links(markdown_body)

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

        images.append(
            {
                "url": src,
                "description": item.get("desc") or item.get("alt"),
                "score": item.get("score"),
            }
        )

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

    soup = BeautifulSoup(html_source, "html.parser")
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

    soup = BeautifulSoup(html_source, "html.parser")
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

    soup = BeautifulSoup(html_source, "html.parser")
    title_tag = soup.find("title")
    if title_tag and title_tag.text:
        return title_tag.text.strip()

    return None


def build_run_config(depth: str, timeout_seconds: float) -> CrawlerRunConfig:
    """
    Build CrawlerRunConfig based on extraction depth.

    Creates optimized configuration for either "basic" (fast) or
    "advanced" (thorough) extraction modes. Excludes navigation elements
    and applies aggressive pruning filter to focus on main content.

    Also enables anti-bot detection features:
    - magic: Auto-handles common bot detection patterns
    - simulate_user: Simulates human mouse movements
    - override_navigator: Spoofs browser navigator properties

    Args:
        depth: "basic" or "advanced"
        timeout_seconds: Timeout in seconds (minimum 3s)

    Returns:
        CrawlerRunConfig: Configuration tuned for requested depth
    """
    timeout_ms = int(max(timeout_seconds, 3) * 1000)
    is_advanced = depth == "advanced"

    # Content filter to remove low-relevance sections
    # Higher threshold = more aggressive filtering (0.0-1.0 scale)
    # Advanced mode uses slightly lower threshold to capture more detail
    prune_filter = PruningContentFilter(
        threshold=0.5 if is_advanced else 0.6,  # Aggressive filtering to reduce noise
        threshold_type="fixed",
        min_word_threshold=12 if is_advanced else 15,  # Require substantial blocks
    )

    # Markdown generator with content filtering
    md_generator = DefaultMarkdownGenerator(content_filter=prune_filter)

    return CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        check_robots_txt=False,  # Disabled to allow extraction from all sites
        remove_overlay_elements=True,
        process_iframes=is_advanced,  # Only process iframes in advanced mode
        excluded_tags=EXCLUDED_TAGS,  # Remove nav, header, footer, aside, etc.
        word_count_threshold=10 if is_advanced else 12,  # Filter out short noise blocks
        page_timeout=timeout_ms,
        delay_before_return_html=1.5 if is_advanced else 0.3,  # Wait for dynamic content to load
        markdown_generator=md_generator,
        # Anti-bot detection features to bypass protected sites
        magic=True,  # Auto-handle common bot detection patterns
        simulate_user=True,  # Simulate human-like mouse movements
        override_navigator=True,  # Spoof navigator properties (webdriver, plugins)
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
        headers = result.response_headers
        try:
            metadata["response_headers"] = dict(headers)
        except Exception:
            metadata["response_headers"] = headers

    # Add error message if present
    if getattr(result, "error_message", None):
        metadata["error_message"] = result.error_message

    return metadata


# =============================================================================
# PDF Extraction Utilities
# =============================================================================


def is_pdf_url(url: str) -> bool:
    """
    Check if URL likely points to a PDF file.

    Checks URL path extension (case-insensitive).
    Does NOT make HTTP requests - just examines the URL string.

    Args:
        url: URL string to check

    Returns:
        True if URL path ends with .pdf, False otherwise
    """
    try:
        parsed = urlparse(url)
        path = parsed.path.lower()
        return path.endswith(".pdf")
    except Exception:
        return False


async def extract_pdf_text(
    url: str,
    timeout: float = 30.0,
    max_size_mb: float = 50.0,
    max_pages: int = 10,
) -> tuple[str | None, str | None]:
    """
    Download and extract text from a PDF URL.

    Uses PyMuPDF (fitz) for text extraction. Only extracts text-based PDFs,
    not scanned images (no OCR). Respects size and page limits.

    Args:
        url: URL of the PDF to download
        timeout: Download timeout in seconds
        max_size_mb: Maximum PDF size in megabytes (default 50MB)
        max_pages: Maximum number of pages to extract (default 10)

    Returns:
        Tuple of (extracted_text, error_message)
        - On success: (text_content, None)
        - On failure: (None, error_description)
    """
    max_size_bytes = int(max_size_mb * 1024 * 1024)

    # Download PDF
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=timeout),
                headers={"User-Agent": config.scraper_user_agent},
            ) as response:
                # Check HTTP status
                if response.status != 200:
                    return None, f"http_error_{response.status}"

                # Check content type (optional, some servers don't set it correctly)
                content_type = response.headers.get("Content-Type", "")
                if content_type and "pdf" not in content_type.lower():
                    # Not a PDF despite URL extension
                    return None, "not_pdf"

                # Check size from headers if available
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > max_size_bytes:
                    return None, "pdf_too_large"

                # Download with size limit
                pdf_bytes = await response.read()
                if len(pdf_bytes) > max_size_bytes:
                    return None, "pdf_too_large"

    except TimeoutError:
        return None, "download_timeout"
    except aiohttp.ClientError as e:
        return None, f"download_error: {type(e).__name__}"
    except Exception as e:
        return None, f"download_failed: {type(e).__name__}"

    # Extract text from PDF
    try:
        # Open PDF from bytes
        pdf_stream = io.BytesIO(pdf_bytes)
        doc = fitz.open(stream=pdf_stream, filetype="pdf")

        # Limit pages to extract (default 10 to avoid processing huge documents)
        total_pages = len(doc)
        pages_to_extract = min(total_pages, max_pages)

        # Extract text from limited number of pages
        text_parts = []
        for page_num in range(pages_to_extract):
            page = doc[page_num]
            page_text = page.get_text("text")
            if page_text and page_text.strip():
                text_parts.append(page_text.strip())

        doc.close()

        # Combine extracted pages
        full_text = "\n\n".join(text_parts)

        # Add note if document was truncated
        if total_pages > max_pages:
            full_text += (
                f"\n\n[Note: PDF truncated. Showing {pages_to_extract} of {total_pages} pages]"
            )

        if not full_text.strip():
            # PDF has no extractable text (likely scanned images)
            return None, "no_text_content"

        return full_text, None

    except Exception as e:
        return None, f"pdf_parse_error: {type(e).__name__}"


def extract_pdf_title(url: str, pdf_bytes: bytes | None = None) -> str | None:
    """
    Extract title from PDF metadata or derive from URL.

    Tries PDF metadata first, falls back to filename from URL.

    Args:
        url: URL of the PDF (used for fallback filename extraction)
        pdf_bytes: Optional PDF bytes to extract metadata from

    Returns:
        Title string or None if not found
    """
    # Try to extract from PDF metadata if bytes provided
    if pdf_bytes:
        try:
            pdf_stream = io.BytesIO(pdf_bytes)
            doc = fitz.open(stream=pdf_stream, filetype="pdf")
            metadata = doc.metadata
            doc.close()

            if metadata and metadata.get("title"):
                return metadata["title"].strip()
        except Exception:
            pass

    # Fallback: extract filename from URL
    try:
        parsed = urlparse(url)
        path = parsed.path
        # Get filename without extension
        filename = path.split("/")[-1]
        if filename.lower().endswith(".pdf"):
            filename = filename[:-4]
        # Clean up common URL encoding
        filename = filename.replace("%20", " ").replace("_", " ").replace("-", " ")
        if filename:
            return filename.strip()
    except Exception:
        pass

    return None
