"""Парсер рейтингов HR-лидеров на hr-ratings.com (Tilda)."""

from __future__ import annotations

import hashlib
import logging
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from tender_agents.channels.page_fetch import fetch_page_html
from tender_agents.channels.people_leads import profiles_to_leads

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9",
}

_LEADER_H2_RE = re.compile(r"^(\d+)\.\s+(.+?),\s*(.+?)\s*$")
_LIST_LEADER_RE = re.compile(
    r"(?P<rank>\d+)\.\s+(?P<name>[А-ЯЁA-Z][а-яёa-z\-]+(?:\s+[А-ЯЁA-Z][а-яёa-z\-]+)+)"
    r",\s*(?P<company>[^(\n—]+?)(?:\s*\((?P<score>\d+)\s*балл)?",
    re.UNICODE,
)
_COMPANY_LINE_RE = re.compile(
    r"Компания:\s*(.+?)(?:\.|Должность:)",
    re.I | re.DOTALL,
)
_POSITION_LINE_RE = re.compile(r"Должность:\s*(.+?)(?:\.|Финансовое)", re.I | re.DOTALL)
_FIO_RE = re.compile(
    r"^[А-ЯЁA-Z][а-яёa-z\-]+\s+[А-ЯЁA-Z][а-яёa-z\-]+(?:\s+[А-ЯЁA-Z][а-яёa-z\-]+)?$"
)


def _stable_person_url(article_url: str, name: str, company: str) -> str:
    h = hashlib.sha256(f"{article_url}|{name}|{company}".encode()).hexdigest()[:16]
    return f"{article_url.rstrip('/')}#person-{h}"


def _page_title(soup: BeautifulSoup) -> str:
    h1 = soup.select_one("h1")
    if h1:
        return h1.get_text(" ", strip=True)[:300]
    if soup.title:
        return soup.title.get_text(" ", strip=True)[:300]
    return "HR-рейтинг"


def _collect_section_text(start_tag, *, stop_at_h2: bool = True) -> str:
    parts: list[str] = []
    sib = start_tag.find_next_sibling()
    while sib:
        if sib.name == "h2" and stop_at_h2:
            cls = " ".join(sib.get("class") or [])
            if "t220__title" in cls or leader_h2_text(sib.get_text(" ", strip=True)):
                break
        if sib.name in ("h2", "h3") and stop_at_h2:
            break
        if sib.name in ("p", "div", "ul", "ol"):
            tx = sib.get_text("\n", strip=True)
            if tx and len(tx) > 15:
                parts.append(tx)
        sib = sib.find_next_sibling()
    return "\n\n".join(parts)[:8000]


def leader_h2_text(text: str) -> bool:
    return bool(_LEADER_H2_RE.match(text.strip()))


def parse_hr_ratings_html(html: str, *, article_url: str) -> tuple[str, list[dict]]:
    """
    Список профилей: name, company, role, rank, bio, score (optional).
    """
    soup = BeautifulSoup(html, "lxml")
    headline = _page_title(soup)
    profiles: list[dict] = []
    seen: set[str] = set()

    for h2 in soup.select("h2"):
        title = h2.get_text(" ", strip=True)
        m = _LEADER_H2_RE.match(title)
        if not m:
            continue
        rank, name, company = m.group(1), m.group(2).strip(), m.group(3).strip()
        if not _FIO_RE.match(name):
            continue
        bio = _collect_section_text(h2)
        role = ""
        cm = _POSITION_LINE_RE.search(bio[:1200])
        if cm:
            role = cm.group(1).strip()[:512]
        key = f"{name}|{company}".lower()
        if key in seen:
            continue
        seen.add(key)
        profiles.append(
            {
                "name": name,
                "company": company,
                "role": role,
                "rank": rank,
                "bio": bio,
                "score": None,
            }
        )

    for h2 in soup.select("h2"):
        if "6-10" not in h2.get_text(" ", strip=True).lower() and "топ 6" not in h2.get_text(" ", strip=True).lower():
            continue
        block = _collect_section_text(h2, stop_at_h2=True)
        for m in _LIST_LEADER_RE.finditer(block):
            name = m.group("name").strip()
            company = m.group("company").strip().rstrip("—").strip()
            if not _FIO_RE.match(name):
                continue
            key = f"{name}|{company}".lower()
            if key in seen:
                continue
            seen.add(key)
            tail_start = m.end()
            tail = block[tail_start : tail_start + 800].strip()
            if tail.startswith("—"):
                tail = tail[1:].strip()
            role = ""
            rm = re.match(r"^([^.—]+?)(?:\.|$)", tail)
            if rm:
                role = rm.group(1).strip()[:512]
            profiles.append(
                {
                    "name": name,
                    "company": company,
                    "role": role,
                    "rank": m.group("rank"),
                    "bio": tail[:4000] if tail else "",
                    "score": m.group("score"),
                }
            )
        break

    return headline, profiles


async def ingest_hr_ratings_url(url: str, *, html_file: str | None = None) -> list[TenderLead]:
    host = urlparse(url).netloc.lower()
    if "hr-ratings.com" not in host:
        raise ValueError("Ожидается URL на hr-ratings.com")

    if html_file:
        from pathlib import Path

        html = Path(html_file).expanduser().read_text(encoding="utf-8", errors="replace")
    else:
        html = await fetch_page_html(url)

    headline, profiles = parse_hr_ratings_html(html, article_url=url)
    if len(profiles) < 3:
        logger.info("hr-ratings native parser: %s профилей, пробуем Yandex", len(profiles))
        from tender_agents.channels.rating_ai_extract import extract_people_with_ai

        ai_profiles = await extract_people_with_ai(html, page_url=url, page_title=headline)
        if ai_profiles:
            profiles = ai_profiles

    if not profiles:
        raise ValueError(
            "Не удалось извлечь участников рейтинга с этой страницы. "
            "Сохраните HTML в браузере и импортируйте: "
            f'tender-leads open ingest "{url}" --html-file page.html'
        )
    return profiles_to_leads(
        profiles,
        article_url=url,
        headline=headline,
        source="hr_ratings",
        channel_kind="hr_ratings",
    )
