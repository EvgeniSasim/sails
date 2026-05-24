"""Сбербанк-АСТ — httpx не даёт поиск по ключу; возвращаем пусто или отфильтрованные ссылки."""

from __future__ import annotations

import httpx
from bs4 import BeautifulSoup

from tender_agents.models import SearchResultItem
from tender_agents.scrape.filters import filter_search_items

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; TenderLeadAgents/0.1)"}


async def search(keyword: str, *, search_url: str, base_url: str, max_items: int = 20) -> list[SearchResultItem]:
    async with httpx.AsyncClient(headers=HEADERS, timeout=45.0, follow_redirects=True) as client:
        resp = await client.get(search_url)
        resp.raise_for_status()
        html = resp.text

    soup = BeautifulSoup(html, "lxml")
    items: list[SearchResultItem] = []
    for a in soup.find_all("a", href=True):
        title = a.get_text(strip=True)
        href = a["href"]
        if len(title) < 25:
            continue
        if "purchase" not in href.lower() and "procedure" not in href.lower():
            continue
        url = href if href.startswith("http") else f"{base_url.rstrip('/')}/{href.lstrip('/')}"
        items.append(SearchResultItem(title=title[:500], url=url))

    return filter_search_items(items[:max_items], keyword=keyword, source_id="sberbank_ast")
