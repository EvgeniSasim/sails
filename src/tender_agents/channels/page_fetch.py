"""Загрузка HTML страницы: httpx, при 403 — Playwright."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.5",
}


async def fetch_page_html(url: str) -> str:
    url = url.strip()
    last_err: Exception | None = None
    try:
        async with httpx.AsyncClient(
            headers=DEFAULT_HEADERS,
            timeout=45.0,
            follow_redirects=True,
        ) as client:
            r = await client.get(url)
            if r.status_code == 403:
                logger.info("fetch_page_html: 403 for %s, trying Playwright", url[:80])
                return await _fetch_playwright(url)
            r.raise_for_status()
            if len(r.text or "") < 400:
                return await _fetch_playwright(url)
            return r.text
    except Exception as e:
        last_err = e
        logger.warning("httpx fetch failed %s: %s", url[:60], e)

    try:
        return await _fetch_playwright(url)
    except Exception as pw_err:
        raise RuntimeError(
            f"Не удалось загрузить страницу: {url[:100]}. "
            f"httpx: {last_err}; playwright: {pw_err}"
        ) from pw_err


async def _fetch_playwright(url: str) -> str:
    from tender_agents.scrape.backends.playwright_backend import PlaywrightBackend

    backend = PlaywrightBackend()
    return await backend._fetch(url)
