"""B2B-Center — парсер списка процедур (без полноценного поиска по ключу на httpx)."""

from __future__ import annotations

import re
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from tender_agents.models import SearchResultItem
from tender_agents.scrape.filters import filter_search_items, is_relevant_to_keyword

BASE = "https://www.b2b-center.ru"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; TenderLeadAgents/0.1)", "Accept-Language": "ru-RU"}


async def search(keyword: str, *, search_url: str, max_items: int = 20) -> list[SearchResultItem]:
    """Без JS полноценный поиск недоступен — парсим ленту и фильтруем по ключу."""
    async with httpx.AsyncClient(headers=HEADERS, timeout=90.0, follow_redirects=True) as client:
        resp = await client.get(search_url)
        resp.raise_for_status()
        html = resp.text

    soup = BeautifulSoup(html, "lxml")
    items: list[SearchResultItem] = []
    seen: set[str] = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        title = a.get_text(strip=True)
        if len(title) < 20:
            continue
        if not re.search(r"(?i)запрос|процедура|конкурс|аукцион", title):
            continue
        if "№" not in title and "tender-" not in href:
            continue
        full = urljoin(BASE, href)
        norm = full.split("#")[0]
        if norm in seen:
            continue
        seen.add(norm)
        m = re.search(r"(?:№|tender-)\s*(\d{6,})", title + href)
        external_id = m.group(1) if m else None
        items.append(
            SearchResultItem(
                title=title[:500],
                url=norm,
                external_id=external_id,
            )
        )

    filtered = [i for i in items if is_relevant_to_keyword(i.title, keyword)]
    return filter_search_items(filtered[:max_items], keyword=keyword, source_id="b2b_center")
