"""HTTP client for fetching data from arbitrary public APIs."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class FetchResult:
    """Successful or failed fetch outcome for a single URL."""

    url: str
    success: bool
    status_code: int | None = None
    content_type: str | None = None
    body: Any = None
    raw_text: str | None = None
    error: str | None = None


class ApiFetcher:
    """Generic HTTP fetcher with timeout and light retry support."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def fetch(self, url: str) -> FetchResult:
        """Fetch a URL and return a structured result. Never raises for HTTP/network errors."""
        headers = {"User-Agent": self.settings.http_user_agent, "Accept": "application/json, */*"}
        timeout = httpx.Timeout(self.settings.http_timeout_seconds)
        attempts = self.settings.http_max_retries + 1
        last_error: str | None = None

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
            for attempt in range(1, attempts + 1):
                try:
                    logger.info("Fetching URL (attempt %s/%s): %s", attempt, attempts, url)
                    response = await client.get(url)
                    content_type = response.headers.get("content-type")
                    body: Any
                    raw_text = response.text

                    if "application/json" in (content_type or "") or raw_text.lstrip().startswith(("{", "[")):
                        try:
                            body = response.json()
                        except ValueError:
                            body = raw_text
                    else:
                        body = raw_text

                    if response.is_success:
                        logger.info("Fetched %s -> HTTP %s", url, response.status_code)
                        return FetchResult(
                            url=url,
                            success=True,
                            status_code=response.status_code,
                            content_type=content_type,
                            body=body,
                            raw_text=raw_text,
                        )

                    last_error = f"HTTP {response.status_code}: {raw_text[:500]}"
                    # Retry only on transient server errors.
                    if response.status_code < 500 or attempt == attempts:
                        logger.warning("Fetch failed for %s: %s", url, last_error)
                        return FetchResult(
                            url=url,
                            success=False,
                            status_code=response.status_code,
                            content_type=content_type,
                            error=last_error,
                        )

                except httpx.TimeoutException:
                    last_error = f"Request timed out after {self.settings.http_timeout_seconds}s"
                    logger.warning("Timeout fetching %s (attempt %s)", url, attempt)
                except httpx.RequestError as exc:
                    last_error = f"Request error: {exc}"
                    logger.warning("Request error for %s (attempt %s): %s", url, attempt, exc)

                if attempt < attempts:
                    await asyncio.sleep(0.5 * attempt)

        return FetchResult(url=url, success=False, error=last_error or "Unknown fetch error")

    async def fetch_many(self, urls: list[str]) -> list[FetchResult]:
        """Fetch multiple URLs concurrently."""
        tasks = [self.fetch(url) for url in urls]
        return list(await asyncio.gather(*tasks))
