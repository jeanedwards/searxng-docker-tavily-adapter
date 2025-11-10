"""
In-memory response caching utilities for FastAPI endpoints.

This module provides a lightweight, reusable helper around cachetools'
TTLCache to store serialized endpoint responses keyed by request payloads.
It keeps the implementation simple and avoids pulling in heavier caching
libraries while still supporting concurrency via asyncio locks.
"""

from __future__ import annotations

import asyncio
from collections.abc import Hashable
from copy import deepcopy
from typing import Any

from cachetools import TTLCache


class ResponseCache:
    """
    Lightweight async-safe TTL cache for FastAPI response payloads.

    Uses cachetools.TTLCache underneath with a per-instance asyncio.Lock
    to protect concurrent access. Stored payloads are deep copied when
    retrieved or saved so route handlers cannot mutate shared state.
    """

    def __init__(self, *, max_entries: int, ttl_seconds: int) -> None:
        self._cache: TTLCache[Hashable, Any] = TTLCache(
            maxsize=max_entries,
            ttl=ttl_seconds,
        )
        # The lock is created lazily so we never interact with asyncio
        # primitives before an event loop exists.
        self._lock: asyncio.Lock | None = None

    async def get(self, key: Hashable) -> Any | None:
        """
        Retrieve a cached payload or None.

        Args:
            key: Hashable cache key derived from request data.
        """
        lock = self._ensure_lock()
        async with lock:
            payload = self._cache.get(key)
        if payload is None:
            return None
        # Defensive copy prevents mutations by downstream code.
        return deepcopy(payload)

    async def set(self, key: Hashable, payload: Any) -> None:
        """
        Store a payload in the cache.

        Args:
            key: Hashable cache key derived from request data.
            payload: JSON-serializable response body.
        """
        lock = self._ensure_lock()
        async with lock:
            self._cache[key] = deepcopy(payload)

    def _ensure_lock(self) -> asyncio.Lock:
        """
        Lazily instantiate the asyncio.Lock once an event loop exists.
        """
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock


__all__ = ["ResponseCache"]


