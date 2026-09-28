"""Shared, bounded HTTP access for all external public-data services.

Retries absorb brief upstream failures; the small in-memory cache avoids
re-downloading large national CSV files during repeated analyses.

AI assistance: OpenAI Codex supported drafting and review. See
``AI_ASSISTANCE.md`` for scope, prompts and the full citation.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


@dataclass
class _CacheEntry:
    expires_at: float
    value: Any


class HttpClient:
    """Small HTTP client with bounded retries and an in-memory TTL cache."""

    def __init__(self, timeout: float = 20, cache_ttl: int = 3600) -> None:
        self.timeout = timeout
        self.cache_ttl = cache_ttl
        self._cache: dict[str, _CacheEntry] = {}
        self._lock = threading.Lock()
        retry = Retry(
            total=3,
            backoff_factor=0.4,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET", "POST"),
        )
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "BeeTheMove/1.0"})
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

    def get_json(
        self, url: str, params: dict | None = None, cache: bool = True
    ) -> dict:
        response = self._get(url, params=params, cache=cache)
        return response.json()

    def get_text(
        self,
        url: str,
        params: dict | None = None,
        encoding: str = "utf-8",
        cache: bool = True,
    ) -> str:
        response = self._get(url, params=params, cache=cache)
        response.encoding = encoding
        return response.text

    def post_json(self, url: str, payload: dict, headers: dict | None = None) -> dict:
        response = self.session.post(
            url, json=payload, headers=headers, timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def _get(self, url: str, params: dict | None, cache: bool) -> requests.Response:
        prepared = requests.Request("GET", url, params=params).prepare()
        key = prepared.url or url
        if cache:
            with self._lock:
                entry = self._cache.get(key)
                if entry and entry.expires_at > time.time():
                    return entry.value

        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        if cache:
            with self._lock:
                self._cache[key] = _CacheEntry(time.time() + self.cache_ttl, response)
        return response
