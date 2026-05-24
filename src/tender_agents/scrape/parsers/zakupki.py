"""Бесплатный парсер ЕИС zakupki.gov.ru — без LLM, только httpx + BeautifulSoup."""

from __future__ import annotations

import logging
import re
from datetime import date
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from tender_agents.models import SearchResultItem
from tender_agents.scrape.filters import filter_search_items
from tender_agents.scrape.html_utils import extract_contacts_from_html, extract_inn_from_html, first_heading_text

BASE = "https://zakupki.gov.ru"
logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; TenderLeadAgents/0.1; +https://github.com/)",
    "Accept-Language": "ru-RU,ru;q=0.9",
}


def _fmt_eis_date(d: date) -> str:
    return d.strftime("%d.%m.%Y")


def build_search_url(
    keyword: str,
    page: int = 1,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
) -> str:
    params = {
        "searchString": keyword,
        "morphology": "on",
        "search-filter": "Дате+размещения",
        "pageNumber": str(page),
        "sortDirection": "false",
        "recordsPerPage": "_20",
        "showLotsInfoHidden": "false",
    }
    if date_from:
        params["publishDateFrom"] = _fmt_eis_date(date_from)
    if date_to:
        params["publishDateTo"] = _fmt_eis_date(date_to)
    return f"{BASE}/epz/order/extendedsearch/results.html?{urlencode(params, safe='+')}"


def _link_score(href: str) -> int:
    """Выше = лучше для enrich (printForm часто отдаёт 404)."""
    if "common-info.html" in href and "printForm" not in href:
        return 100
    if "/view/common-info" in href:
        return 95
    if "common-info" in href:
        return 90
    if "printForm/view" in href:
        return 10
    if re.search(r"regNumber=\d+", href) and "documents" not in href and "notice" in href:
        return 50
    if "notice" in href and "documents" not in href:
        return 40
    return 0


def _detail_url_from_block(block: BeautifulSoup) -> str | None:
    reg_el = block.select_one(".registry-entry__header-mid__number")
    reg_number = None
    if reg_el:
        m = re.search(r"№\s*(\d+)", reg_el.get_text())
        reg_number = m.group(1) if m else None

    best_url: str | None = None
    best_score = -1
    for a in block.find_all("a", href=True):
        href = a["href"]
        if "documents" in href and "common-info" not in href:
            continue
        full = urljoin(BASE, href)
        sc = _link_score(href)
        if sc > best_score:
            best_score = sc
            best_url = full

    if best_url and best_score >= 40:
        return normalize_detail_url(best_url)

    if reg_number:
        for a in block.find_all("a", href=True):
            if f"regNumber={reg_number}" in a["href"] and "documents" not in a["href"]:
                return normalize_detail_url(urljoin(BASE, a["href"]))
    return normalize_detail_url(best_url) if best_url else None


def normalize_detail_url(url: str) -> str:
    """Предпочитаем common-info вместо printForm в уже сохранённом URL."""
    if "printForm" not in url:
        return url
    for alt in detail_url_candidates(url):
        if "common-info" in alt and alt != url:
            return alt
    return url


def detail_url_candidates(url: str) -> list[str]:
    """Варианты карточки закупки, если printForm недоступен."""
    out: list[str] = []
    seen: set[str] = set()

    def add(u: str) -> None:
        u = (u or "").strip()
        if u and u not in seen:
            seen.add(u)
            out.append(u)

    add(url)
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    reg = (qs.get("regNumber") or qs.get("purchaseNoticeNumber") or [None])[0]
    guid = (qs.get("purchaseNoticeGuid") or [None])[0]
    path = parsed.path

    if "printForm" in path and reg:
        # notice223-new/printForm/view.html → …/common-info.html
        p1 = re.sub(r"printForm/view\.html", "common-info.html", path, flags=re.I)
        add(f"{BASE}{p1}?regNumber={reg}")
        # …/view/common-info.html (ea20, 44-ФЗ)
        p2 = re.sub(
            r"printForm/view\.html",
            "view/common-info.html",
            path,
            flags=re.I,
        )
        if p2 != path:
            add(f"{BASE}{p2}?regNumber={reg}")
        # без сегмента printForm
        p3 = re.sub(r"/printForm/view\.html", "/common-info.html", path, flags=re.I)
        if p3 != p1:
            add(f"{BASE}{p3}?regNumber={reg}")
        if guid:
            add(f"{BASE}{p1}?regNumber={reg}&purchaseNoticeGuid={guid}")

    # Сначала common-info, printForm — в конце
    return [u for u in out if "printForm" not in u] + [u for u in out if "printForm" in u]


def parse_search_results(html: str, *, keyword: str) -> list[SearchResultItem]:
    soup = BeautifulSoup(html, "lxml")
    items: list[SearchResultItem] = []
    seen: set[str] = set()

    for block in soup.select(".search-registry-entry-block"):
        title_el = block.select_one(".registry-entry__body-value")
        title = title_el.get_text(strip=True) if title_el else ""
        if not title or len(title) < 5:
            continue

        url = _detail_url_from_block(block)
        if not url or url in seen:
            continue
        seen.add(url)

        num_el = block.select_one(".registry-entry__header-mid__number")
        external_id = None
        if num_el:
            m = re.search(r"(\d{10,})", num_el.get_text())
            external_id = m.group(1) if m else None

        cust_el = block.select_one(".registry-entry__body-href a")
        customer = cust_el.get_text(strip=True) if cust_el else None

        status_el = block.select_one(".registry-entry__header-mid__title")
        status_hint = status_el.get_text(strip=True) if status_el else None

        items.append(
            SearchResultItem(
                title=title,
                url=url,
                external_id=external_id,
                status_hint=status_hint,
                customer_hint=customer,
            )
        )
    return items


async def search(
    keyword: str,
    *,
    max_pages: int = 1,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[SearchResultItem]:
    all_items: list[SearchResultItem] = []
    seen: set[str] = set()
    async with httpx.AsyncClient(headers=HEADERS, timeout=60.0, follow_redirects=True) as client:
        for page in range(1, max_pages + 1):
            url = build_search_url(
                keyword,
                page=page,
                date_from=date_from,
                date_to=date_to,
            )
            resp = await client.get(url)
            resp.raise_for_status()
            for item in parse_search_results(resp.text, keyword=keyword):
                if item.url not in seen:
                    seen.add(item.url)
                    all_items.append(item)
    return filter_search_items(all_items, keyword=keyword, source_id="zakupki")


def _parse_detail_html(html: str, *, fallback_title: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    title = first_heading_text(soup, fallback_title)

    customer_name = None
    for label in soup.find_all(string=re.compile(r"Заказчик|Организация", re.I)):
        parent = label.find_parent()
        if parent:
            val = parent.find_next(string=True)
            if val and len(str(val).strip()) > 3:
                customer_name = str(val).strip()[:512]
                break

    price = None
    price_el = soup.find(string=re.compile(r"Начальная\s+цена|НМЦК", re.I))
    if price_el:
        nxt = price_el.find_parent()
        if nxt:
            price = nxt.get_text(" ", strip=True)[:128]

    contacts = extract_contacts_from_html(html)
    return {
        "title": title,
        "customer_name": customer_name,
        "customer_inn": extract_inn_from_html(html),
        "price": price,
        "contacts": [c.model_dump() for c in contacts],
        "description_snippet": soup.get_text(" ", strip=True)[:500],
    }


def _minimal_detail(
    *,
    fallback_title: str,
    url: str,
    customer_hint: str | None = None,
) -> dict:
    return {
        "title": fallback_title or "Закупка",
        "customer_name": customer_hint,
        "customer_inn": None,
        "price": None,
        "contacts": [],
        "description_snippet": f"Карточка ЕИС недоступна (404). URL: {url[:200]}",
        "_enrich_degraded": True,
    }


async def enrich_detail(
    url: str,
    *,
    fallback_title: str = "",
    customer_hint: str | None = None,
) -> dict:
    urls = detail_url_candidates(normalize_detail_url(url))
    last_err: Exception | None = None

    async with httpx.AsyncClient(headers=HEADERS, timeout=60.0, follow_redirects=True) as client:
        for try_url in urls:
            try:
                resp = await client.get(try_url)
                if resp.status_code in (404, 410):
                    logger.debug("zakupki %s → %s", resp.status_code, try_url[:100])
                    last_err = httpx.HTTPStatusError(
                        "not found",
                        request=resp.request,
                        response=resp,
                    )
                    continue
                resp.raise_for_status()
                data = _parse_detail_html(resp.text, fallback_title=fallback_title)
                if try_url != url:
                    data["_detail_url_used"] = try_url
                return data
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (404, 410):
                    last_err = e
                    continue
                raise

    logger.warning(
        "zakupki enrich: все URL недоступны (%s), сохраняем краткую карточку",
        url[:90],
    )
    return _minimal_detail(
        fallback_title=fallback_title,
        url=url,
        customer_hint=customer_hint,
    )
