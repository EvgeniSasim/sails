"""Бесплатный бэкенд по умолчанию: httpx + HTML-парсеры + regex для контактов."""

from __future__ import annotations

from typing import Any

import httpx

from tender_agents.scrape.base import ExtractBackend
from tender_agents.scrape.html_utils import extract_contacts_from_html, extract_inn_from_html, first_heading_text
from tender_agents.scrape.prompts import TENDER_DETAIL_PROMPT, TENDER_LIST_PROMPT

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; TenderLeadAgents/0.1)",
    "Accept-Language": "ru-RU,ru;q=0.9",
}


class HttpxFreeBackend(ExtractBackend):
    """Без API-ключей. Для zakupki — отдельный парсер в адаптере; для остальных — базовый HTML."""

    name = "httpx"

    async def _fetch(self, url: str) -> str:
        async with httpx.AsyncClient(
            headers=HEADERS, timeout=90.0, follow_redirects=True
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text

    async def extract_list(self, url: str, *, keyword: str, source_name: str) -> dict[str, Any]:
        html = await self._fetch(url)
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        items: list[dict] = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            if len(text) < 15:
                continue
            if not any(
                x in href.lower()
                for x in ("tender", "purchase", "notice", "lot", "trade", "zakup", "market")
            ):
                continue
            full = href if href.startswith("http") else url.rsplit("/", 1)[0] + "/" + href.lstrip("/")
            items.append(
                {
                    "title": text[:300],
                    "url": full,
                    "status_hint": None,
                    "customer_hint": None,
                }
            )
            if len(items) >= 30:
                break
        return {"items": items, "_prompt": TENDER_LIST_PROMPT, "_keyword": keyword}

    async def extract_detail(self, url: str, *, keyword: str) -> dict[str, Any]:
        html = await self._fetch(url)
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        contacts = extract_contacts_from_html(html)
        return {
            "title": first_heading_text(soup),
            "customer_inn": extract_inn_from_html(html),
            "contacts": [c.model_dump() for c in contacts],
            "description_snippet": soup.get_text(" ", strip=True)[:400],
            "_prompt": TENDER_DETAIL_PROMPT,
            "_keyword": keyword,
        }
