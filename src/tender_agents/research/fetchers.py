"""Pluggable HTTP fetch for contact research."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

import httpx

from tender_agents.agents.profile_enrich_agent import HEADERS

logger = logging.getLogger(__name__)

CAPTCHA_MARKERS = (
    "showcaptcha",
    "checkbox-captcha",
    "captcha__",
    "not a robot",
    "подтвердите, что запросы",
    "smartcaptcha",
)


@dataclass
class FetchResult:
    url: str
    status_code: int = 0
    html: str = ""
    error: str = ""
    captcha: bool = False
    headers_used: dict[str, str] = field(default_factory=dict)


def detect_captcha(html: str) -> bool:
    if not html:
        return False
    low = html.lower()
    return any(m in low for m in CAPTCHA_MARKERS)


async def fetch_url(
    url: str,
    *,
    cookies: dict[str, str] | None = None,
    extra_headers: dict[str, str] | None = None,
    timeout: float = 45.0,
) -> FetchResult:
    headers = {**HEADERS, **(extra_headers or {})}
    try:
        async with httpx.AsyncClient(
            headers=headers,
            cookies=cookies or {},
            timeout=timeout,
            follow_redirects=True,
        ) as client:
            resp = await client.get(url)
            html = resp.text or ""
            cap = detect_captcha(html) or resp.status_code in (403, 429)
            return FetchResult(
                url=str(resp.url),
                status_code=resp.status_code,
                html=html,
                captcha=cap,
                error="" if resp.is_success and not cap else f"HTTP {resp.status_code}",
            )
    except Exception as e:
        logger.debug("fetch_url %s: %s", url[:80], e)
        return FetchResult(url=url, error=str(e)[:300])


class HttpxFetcher:
    async def fetch(self, url: str, *, cookies: dict[str, str] | None = None) -> FetchResult:
        return await fetch_url(url, cookies=cookies)


class ManualCaptchaFetcher(HttpxFetcher):
    """Same as httpx; job layer sets needs_captcha when detect_captcha is true."""


class ExternalCaptchaFetcher(HttpxFetcher):
    """Optional third-party solver via env (stub — delegates to httpx if unset)."""

    def __init__(self) -> None:
        self._service_url = (os.environ.get("CAPTCHA_SERVICE_URL") or "").strip()
        self._api_key = (os.environ.get("CAPTCHA_API_KEY") or "").strip()

    async def fetch(self, url: str, *, cookies: dict[str, str] | None = None) -> FetchResult:
        if not self._service_url or not self._api_key:
            return await super().fetch(url, cookies=cookies)
        logger.info("CAPTCHA_SERVICE_URL configured but solver not implemented — httpx fallback")
        return await super().fetch(url, cookies=cookies)
