import abc
import logging
import os
from typing import Optional

import httpx
from tender_agents.agents.profile_enrich_agent import HEADERS

logger = logging.getLogger(__name__)

class Fetcher(abc.ABC):
    @abc.abstractmethod
    async def fetch(self, url: str) -> str:
        """Fetch HTML content from the given URL."""
        pass

class HttpxFetcher(Fetcher):
    def __init__(self, timeout: float = 30.0, cookies: dict | None = None):
        self.timeout = timeout
        self.cookies = cookies or {}

    async def fetch(self, url: str) -> str:
        async with httpx.AsyncClient(
            headers=HEADERS, timeout=self.timeout, follow_redirects=True, cookies=self.cookies
        ) as client:
            r = await client.get(url)
            # We don't raise_for_status here immediately because captchas
            # often return 403 or 429 which we want to inspect.
            return r.text

class CaptchaException(Exception):
    def __init__(self, engine: str, url: str, message: str = "Captcha detected"):
        self.engine = engine
        self.url = url
        self.message = message
        super().__init__(self.message)

class ManualCaptchaFetcher(Fetcher):
    """
    Throws CaptchaException if captcha markers are detected.
    The job should be paused and the URL exposed for the manager.
    """
    def __init__(self, inner: Fetcher):
        self.inner = inner
        self.captcha_markers = (
            "showcaptcha",
            "captcha",
            "checkbox-captcha",
            "not a robot",
            "подтвердите, что запросы",
        )

    async def fetch(self, url: str) -> str:
        html = await self.inner.fetch(url)
        low = html.lower()
        if any(m in low for m in self.captcha_markers):
            engine = "yandex" if "yandex" in url else "generic"
            raise CaptchaException(engine=engine, url=url)
        return html

class ExternalCaptchaFetcher(Fetcher):
    """
    Stub for external captcha solving services.
    Reads CAPTCHA_SERVICE_URL and CAPTCHA_API_KEY from environment.
    """
    def __init__(self, inner: Fetcher):
        self.inner = inner
        self.service_url = os.getenv("CAPTCHA_SERVICE_URL")
        self.api_key = os.getenv("CAPTCHA_API_KEY")

    async def fetch(self, url: str) -> str:
        # In a real implementation, this would use a third-party API to solve captcha
        # For now, it just delegates to the inner fetcher or logs the requirement.
        if self.service_url and self.api_key:
            logger.info("External captcha service configured at %s, but solver is a stub.", self.service_url)
        return await self.inner.fetch(url)
