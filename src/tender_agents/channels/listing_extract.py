"""Извлечение ЛПР со страниц-каталогов (списки карточек, без обхода каждой карточки)."""

from __future__ import annotations

import asyncio
import logging
import re
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Лимит страниц каталога за один импорт (защита от бесконечного обхода)
MAX_CATALOG_PAGES = 50
_PAGINATION_QUERY_KEYS = frozenset(
    {"offset", "page", "p", "pagen", "pagen_1", "start", "from"}
)

_PERSON_ID_HREF = re.compile(r"/person/id/(\d+)", re.I)
_FIO_LOOSE = re.compile(
    r"^[А-ЯЁA-Z][а-яёa-zА-ЯЁA-Z\-]+\s+"
    r"[А-ЯЁA-Z][а-яёa-z\-]+(?:\s+[А-ЯЁA-Z][а-яёa-z\-]+)?$"
)


def _normalize_person_name(raw: str) -> str:
    s = re.sub(r"\s+", " ", (raw or "").strip())
    if s.isupper() and len(s) > 5:
        parts = s.split()
        return " ".join(p.capitalize() if p.isupper() and len(p) > 1 else p for p in parts)
    return s


def count_person_links(html: str) -> int:
    soup = BeautifulSoup(html, "lxml")
    return len(_collect_person_ids(soup))


def _collect_person_ids(soup: BeautifulSoup) -> set[str]:
    ids: set[str] = set()
    for a in soup.find_all("a", href=_PERSON_ID_HREF):
        m = _PERSON_ID_HREF.search(a.get("href") or "")
        if m:
            ids.add(m.group(1))
    return ids


def _lines_from_card(anchor) -> list[str]:
    block = anchor
    for _ in range(8):
        if block.parent is None:
            break
        block = block.parent
        lines = [
            ln.strip()
            for ln in block.get_text("\n", strip=True).split("\n")
            if ln.strip() and "читать далее" not in ln.lower()
        ]
        if len(lines) >= 2:
            return lines
    return []


def _role_company_from_lines(lines: list[str], name: str) -> tuple[str, str]:
    rest = [ln for ln in lines if ln != name]
    if not rest:
        return "", "—"
    if len(rest) == 1:
        return rest[0][:512], "—"
    role = rest[0][:512]
    company = rest[1][:512] if len(rest) > 1 else "—"
    if len(company) < len(role) and len(rest) >= 2:
        # короткое название компании обычно последнее перед «читать далее»
        company = rest[-1][:512] if rest[-1] != role else company
    return role, company


def parse_person_listing_html(html: str, *, page_url: str) -> list[dict]:
    """
    Каталоги вида globalmsk.ru/person/cat/… — ссылки /person/id/N и блоки с должностью/компанией.
    """
    soup = BeautifulSoup(html, "lxml")
    base = f"{urlparse(page_url).scheme}://{urlparse(page_url).netloc}"
    seen_ids: set[str] = set()
    profiles: list[dict] = []

    for a in soup.find_all("a", href=_PERSON_ID_HREF):
        m = _PERSON_ID_HREF.search(a.get("href") or "")
        if not m:
            continue
        pid = m.group(1)
        if pid in seen_ids:
            continue
        raw_name = a.get_text(" ", strip=True)
        if not raw_name or len(raw_name) < 6 or "читать" in raw_name.lower():
            continue
        name = _normalize_person_name(raw_name)
        if len(name.split()) < 2:
            continue
        seen_ids.add(pid)
        lines = _lines_from_card(a)
        role, company = _role_company_from_lines(lines, raw_name)
        if not role and len(lines) > 1:
            role, company = _role_company_from_lines(lines, name)
        profile_url = urljoin(base, f"/person/id/{pid}")
        profiles.append(
            {
                "name": name,
                "company": company or "—",
                "role": role,
                "rank": str(len(profiles) + 1),
                "bio": f"Каталог: {page_url}\nКарточка: {profile_url}",
                "profile_url": profile_url,
                "person_id": pid,
            }
        )

    return profiles


def _catalog_canonical_url(url: str) -> str:
    """Первая страница каталога без query (для сравнения пути)."""
    p = urlparse(url.strip().split("#")[0])
    return f"{p.scheme}://{p.netloc}{p.path}"


def _is_catalog_listing_url(url: str, catalog_path: str) -> bool:
    p = urlparse(url)
    if p.path != catalog_path:
        return False
    if not p.query:
        return True
    qs = parse_qs(p.query)
    return any(k.lower() in _PAGINATION_QUERY_KEYS for k in qs)


def discover_catalog_page_urls(html: str, *, page_url: str) -> set[str]:
    """Все URL страниц пагинации того же каталога (offset=, page=, .pager)."""
    soup = BeautifulSoup(html, "lxml")
    catalog_path = urlparse(page_url).path
    found: set[str] = {_catalog_canonical_url(page_url), page_url.split("#")[0]}

    def _add(href: str) -> None:
        if not href or href.startswith("#") or href.startswith("javascript:"):
            return
        full = urljoin(page_url, href).split("#")[0]
        if _is_catalog_listing_url(full, catalog_path):
            found.add(full)

    for a in soup.find_all("a", href=True):
        _add(a["href"])

    for a in soup.select(".pager a, .pagination a, [class*='pager'] a, [class*='paginat'] a"):
        _add(a.get("href") or "")

    return found


def _merge_profile_row(existing: dict, new: dict) -> None:
    """Один person_id — дополняем поля с другой страницы каталога."""
    if len((new.get("role") or "")) > len((existing.get("role") or "")):
        existing["role"] = new["role"]
    if (new.get("company") or "—") != "—" and (
        existing.get("company") in (None, "", "—")
        or len(new.get("company", "")) > len(existing.get("company", ""))
    ):
        existing["company"] = new["company"]
    old_bio = (existing.get("bio") or "").strip()
    new_bio = (new.get("bio") or "").strip()
    if new_bio and new_bio not in old_bio:
        existing["bio"] = (old_bio + "\n" + new_bio).strip()[:8000] if old_bio else new_bio


async def crawl_listing_catalog(
    start_url: str,
    *,
    html_first: str | None = None,
    fetch_html,
    max_pages: int = MAX_CATALOG_PAGES,
    min_links: int = 8,
) -> list[dict]:
    """
    Обход всех страниц пагинации каталога; дедуп по person_id.
    html_first — уже загруженная первая страница (из ingest).
    """
    queue: list[str] = [_catalog_canonical_url(start_url)]
    seen_pages: set[str] = set()
    by_person: dict[str, dict] = {}
    pages_done = 0

    from tender_agents.settings import settings

    delay = settings.request_delay_sec

    while queue and pages_done < max_pages:
        page_url = queue.pop(0)
        key = page_url.split("#")[0]
        if key in seen_pages:
            continue
        seen_pages.add(key)

        if pages_done == 0 and html_first is not None:
            html = html_first
        else:
            if pages_done > 0 and delay > 0:
                await asyncio.sleep(delay)
            html = await fetch_html(page_url)

        pages_done += 1
        if count_person_links(html) < min_links:
            continue

        for p in parse_person_listing_html(html, page_url=page_url):
            pid = str(p.get("person_id") or p["name"])
            if pid in by_person:
                _merge_profile_row(by_person[pid], p)
            else:
                by_person[pid] = p

        for next_url in discover_catalog_page_urls(html, page_url=page_url):
            nk = next_url.split("#")[0]
            if nk not in seen_pages and nk not in queue:
                queue.append(nk)

    profiles = list(by_person.values())
    if profiles:
        logger.info(
            "Catalog crawl: %s профилей, %s страниц каталога, старт %s",
            len(profiles),
            pages_done,
            start_url[:80],
        )
    return profiles


def try_extract_listing(html: str, *, page_url: str, min_links: int = 8) -> list[dict]:
    """Одна страница каталога (без пагинации). Для полного обхода — crawl_listing_catalog."""
    n_links = count_person_links(html)
    if n_links < min_links:
        return []
    profiles = parse_person_listing_html(html, page_url=page_url)
    if profiles:
        logger.info(
            "Listing extract: %s профилей (ссылок /person/id/: %s) %s",
            len(profiles),
            n_links,
            page_url[:80],
        )
    return profiles


async def try_extract_listing_with_pagination(
    start_url: str,
    *,
    html_first: str | None = None,
    fetch_html=None,
    min_links: int = 8,
) -> list[dict]:
    """Каталог + обход пагинации; иначе одна страница."""
    if fetch_html is None:
        from tender_agents.channels.page_fetch import fetch_page_html as fetch_html

    html = html_first
    if html is None:
        html = await fetch_html(start_url)

    if count_person_links(html) < min_links:
        return []

    page_urls = discover_catalog_page_urls(html, page_url=start_url)
    if len(page_urls) > 1:
        return await crawl_listing_catalog(
            start_url,
            html_first=html,
            fetch_html=fetch_html,
            min_links=min_links,
        )
    return try_extract_listing(html, page_url=start_url, min_links=min_links)
