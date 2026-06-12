"""Адаптер zakupki.gov.ru (ЕИС) через httpx, без браузера."""

from __future__ import annotations

import logging
import re
from datetime import date, datetime
from typing import AsyncIterator, List, Optional
from urllib.parse import quote, urljoin, urlparse

from tender_agents.browser.session import HumanSession
from tender_agents.models import CollectFilters, ListingItem, SearchContext, TenderRecord
from tender_agents.platforms.base import PlatformAdapter
from tender_agents.platforms.registry import registry

logger = logging.getLogger(__name__)

_BASE = "https://zakupki.gov.ru"
_SEARCH_URL = (
    _BASE
    + "/epz/order/extendedsearch/results.html"
    + "?searchString={keyword}&pageNumber={page}&sortBy=UPDATE_DATE"
)
_USER_AGENT = (
    "Mozilla/5.0 (compatible; tender-leads/0.2; +https://github.com/EvgeniSasim/sails)"
)


def parse_listing_html(html: str, *, base: str = _BASE) -> List[dict]:
    items: List[dict] = []
    seen: set[str] = set()
    pattern = re.compile(
        r'href="(/epz/order/notice/[^"]*regNumber=(\d+)[^"]*)"[^>]*>\s*([^<]+)',
        re.I,
    )
    for match in pattern.finditer(html):
        path, reg_number, title = match.groups()
        url = urljoin(base, path)
        if url in seen:
            continue
        seen.add(url)
        items.append(
            {
                "url": url,
                "external_id": reg_number,
                "title": re.sub(r"\s+", " ", title).strip(),
            }
        )
    return items


def parse_detail_html(html: str, *, url: str) -> dict:
    text = re.sub(r"\s+", " ", html)
    external_id = None
    id_match = re.search(r"regNumber=(\d+)", url)
    if id_match:
        external_id = id_match.group(1)
    if not external_id:
        id_match = re.search(r"Реестровый номер[^0-9]*(\d{10,})", text, re.I)
        if id_match:
            external_id = id_match.group(1)

    title = None
    title_match = re.search(
        r'class="cardMainInfo__content"[^>]*>([^<]+)|'
        r"Наименование объекта закупки[^<]*</[^>]+>[^<]*<[^>]+>([^<]+)",
        html,
        re.I,
    )
    if title_match:
        title = (title_match.group(1) or title_match.group(2) or "").strip()

    customer = None
    cust_match = re.search(
        r"Размещение осуществляет[^<]*</[^>]+>[^<]*<[^>]+>([^<]+)|"
        r'class="cardMainInfo__title">Организация, осуществляющая размещение</[^>]+>.*?'
        r'class="cardMainInfo__content">([^<]+)',
        html,
        re.I | re.S,
    )
    if cust_match:
        customer = (cust_match.group(1) or cust_match.group(2) or "").strip()

    price = None
    price_match = re.search(
        r"Начальная \(максимальная\) цена контракта[^0-9]*([\d\s.,]+)",
        text,
        re.I,
    )
    if price_match:
        price = price_match.group(1).strip()

    publish_date_str = None
    pub_match = re.search(r"Размещено\s+(\d{2}\.\d{2}\.\d{4})", text, re.I)
    if pub_match:
        publish_date_str = pub_match.group(1)

    deadline_str = None
    dl_match = re.search(
        r"Дата и время окончания подачи заявок\s+(\d{2}\.\d{2}\.\d{4})",
        text,
        re.I,
    )
    if dl_match:
        deadline_str = dl_match.group(1)

    return {
        "external_id": external_id,
        "title": title,
        "customer_name": customer,
        "price": price,
        "publish_date_str": publish_date_str,
        "deadline_str": deadline_str,
    }


def _parse_date(date_str: Optional[str]) -> Optional[date]:
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str.split(" ")[0], "%d.%m.%Y").date()
    except ValueError:
        return None


class ZakupkiAdapter(PlatformAdapter):
    needs_browser = False

    def __init__(self) -> None:
        self._client = None
        self._keyword = ""
        self._filters: CollectFilters | None = None
        self._pages: dict[int, List[dict]] = {}

    def matches_url(self, url: str) -> bool:
        host = urlparse(url).hostname or ""
        return "zakupki.gov.ru" in host

    async def _ensure_client(self) -> None:
        if self._client is not None:
            return
        try:
            import httpx
        except ImportError as e:
            raise RuntimeError(
                "Для zakupki.gov.ru установите httpx: pip install -e '.[httpx]'"
            ) from e
        self._client = httpx.AsyncClient(
            timeout=45.0,
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT, "Accept-Language": "ru-RU,ru;q=0.9"},
        )

    async def _fetch(self, url: str) -> str:
        await self._ensure_client()
        resp = await self._client.get(url)
        if resp.status_code >= 400:
            raise RuntimeError(
                f"zakupki.gov.ru вернул HTTP {resp.status_code}. "
                "Возможна блокировка IP — попробуйте с сервера в РФ."
            )
        return resp.text

    async def open_home(self, session: HumanSession | None):
        await self._ensure_client()

    async def search(
        self, session: HumanSession | None, keyword: str, filters: CollectFilters
    ) -> SearchContext:
        self._keyword = keyword
        self._filters = filters
        self._pages = {}
        await self._load_page(1)
        return SearchContext(keyword=keyword, filters=filters)

    async def _load_page(self, page_num: int) -> List[dict]:
        if page_num in self._pages:
            return self._pages[page_num]
        url = _SEARCH_URL.format(keyword=quote(self._keyword), page=page_num)
        logger.info("Запрос выдачи ЕИС, страница %s", page_num)
        html = await self._fetch(url)
        items = parse_listing_html(html)
        self._pages[page_num] = items
        return items

    async def iter_listing_pages(
        self, session: HumanSession | None, ctx: SearchContext, max_pages: int
    ) -> AsyncIterator[ListingItem]:
        seen: set[str] = set()
        for page_num in range(1, max_pages + 1):
            rows = await self._load_page(page_num)
            if not rows:
                break
            for row in rows:
                norm = row["url"]
                if norm in seen:
                    continue
                seen.add(norm)
                preview = f"№ {row.get('external_id', '')}\n{row.get('title', '')}"
                yield ListingItem(
                    url=row["url"],
                    title=row.get("title"),
                    preview=preview.strip() or None,
                )
            if page_num >= max_pages or len(rows) == 0:
                break

    async def open_detail(
        self,
        session: HumanSession | None,
        item: ListingItem,
        keyword: str,
        filters: CollectFilters,
    ) -> Optional[TenderRecord]:
        html = await self._fetch(str(item.url))
        fields = parse_detail_html(html, url=str(item.url))

        external_id = fields.get("external_id")
        if not external_id and item.preview:
            id_match = re.search(r"№\s*(\d+)", item.preview)
            if id_match:
                external_id = id_match.group(1)
        publish_date = _parse_date(fields.get("publish_date_str"))
        deadline = _parse_date(fields.get("deadline_str"))

        if publish_date:
            if filters.date_from and publish_date < filters.date_from:
                return None
            if filters.date_to and publish_date > filters.date_to:
                return None

        return TenderRecord(
            platform="zakupki.gov.ru",
            external_id=external_id,
            title=fields.get("title") or item.title or "Без названия",
            url=item.url,
            customer_name=fields.get("customer_name"),
            publish_date=publish_date,
            deadline=deadline,
            price=fields.get("price"),
            matched_keyword=keyword,
            raw_snippet=item.preview,
        )

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None


registry.register(ZakupkiAdapter())
