"""Платный облачный ScrapeGraphAI — https://scrapegraphai.com/"""

from __future__ import annotations

from typing import Any

from tender_agents.scrape.base import ExtractBackend
from tender_agents.scrape.client import ScrapeGraphClient
from tender_agents.scrape.prompts import TENDER_DETAIL_PROMPT, TENDER_LIST_PROMPT


class ScrapeGraphBackend(ExtractBackend):
    name = "scrapegraph"

    def __init__(self, client: ScrapeGraphClient | None = None):
        self._client = client or ScrapeGraphClient()

    async def extract_list(self, url: str, *, keyword: str, source_name: str) -> dict[str, Any]:
        prompt = (
            f"{TENDER_LIST_PROMPT}\n"
            f"Ключевое слово: «{keyword}». Источник: {source_name}."
        )
        return await self._client.extract(url, prompt, stealth=True)

    async def extract_detail(self, url: str, *, keyword: str) -> dict[str, Any]:
        prompt = f"{TENDER_DETAIL_PROMPT}\nКонтекст: запрос «{keyword}»."
        return await self._client.extract(url, prompt, stealth=True)
