"""Thin HTTP client for SearXNG interactions."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
from fastapi import HTTPException

from .config_loader import config

DEFAULT_TIMEOUT = 30


class SearxngClient:
    """Encapsulates SearXNG HTTP calls so services stay focused on orchestration."""

    def __init__(self, base_url: str | None = None, logger: logging.Logger | None = None):
        self.base_url = (base_url or config.searxng_url).rstrip("/")
        self.logger = logger or logging.getLogger(self.__class__.__module__)

    async def search(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute a search request against SearXNG and return the parsed JSON body."""
        headers = {
            "X-Forwarded-For": "127.0.0.1",
            "X-Real-IP": "127.0.0.1",
            "User-Agent": "Mozilla/5.0 (compatible; TavilyBot/1.0)",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.base_url}/search",
                    data=params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        self.logger.error(
                            "SearXNG returned %s: %s", response.status, error_text[:500]
                        )
                        raise HTTPException(
                            status_code=500,
                            detail=f"SearXNG request failed with status {response.status}",
                        )
                    return await response.json()
            except TimeoutError:
                raise HTTPException(status_code=504, detail="SearXNG timeout")
            except aiohttp.ClientError as exc:
                self.logger.error("SearXNG connection error: %s", exc)
                raise HTTPException(status_code=503, detail="Cannot connect to search service")
            except Exception as exc:  # noqa: BLE001 - surface unexpected errors
                self.logger.error("SearXNG error: %s", exc)
                raise HTTPException(status_code=500, detail="Search service unavailable") from exc
