"""Yandex AI Studio — агенты извлекают JSON из HTML (httpx + YandexGPT)."""

from __future__ import annotations

from typing import Any

import httpx

from tender_agents.scrape.backends.httpx_llm_free import HEADERS
from tender_agents.scrape.base import ExtractBackend
from tender_agents.yandex.agent_runner import YandexAgentRunner


class YandexBackend(ExtractBackend):
    name = "yandex"

    def __init__(self, runner: YandexAgentRunner | None = None):
        self.runner = runner or YandexAgentRunner()

    async def _fetch(self, url: str) -> str:
        async with httpx.AsyncClient(
            headers=HEADERS, timeout=90.0, follow_redirects=True
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text

    async def extract_list(self, url: str, *, keyword: str, source_name: str) -> dict[str, Any]:
        html = await self._fetch(url)
        return await self.runner.extract_list_from_html(
            html, keyword=keyword, source_name=source_name, page_url=url
        )

    async def extract_detail(self, url: str, *, keyword: str) -> dict[str, Any]:
        html = await self._fetch(url)
        return await self.runner.extract_detail_from_html(html, keyword=keyword, page_url=url)
