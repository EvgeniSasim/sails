"""Парсер материалов kommersant.ru/doc/* с таблицами рейтингов (ФИО, должность, компания)."""

from __future__ import annotations

import hashlib
import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from tender_agents.channels.linkedin_hint import linkedin_people_search_url, yandex_people_search_url
from tender_agents.models import Contact, LeadSegment, TenderLead, TenderStatus

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.5",
    "Referer": "https://www.kommersant.ru/",
}

_FIO_RE = re.compile(
    r"^[А-ЯЁA-Z][а-яёa-z\-]+\s+[А-ЯЁA-Z][а-яёa-z\-]+(?:\s+[А-ЯЁA-Z][а-яёa-z\-]+)?\*?$"
)


def _stable_person_url(article_url: str, name: str, company: str) -> str:
    h = hashlib.sha256(f"{article_url}|{name}|{company}".encode()).hexdigest()[:16]
    return f"{article_url.rstrip('/')}#open-{h}"


def _doc_id_from_url(url: str) -> str | None:
    m = re.search(r"/doc/(\d+)", url)
    return m.group(1) if m else None


def parse_kommersant_ranking_html(html: str, *, article_url: str) -> tuple[str, str, list[dict]]:
    """
    Возвращает (заголовок статьи, дата из <time> если есть, список словарей-профилей).
    Каждый словарь: name, role, company, industry, rank, source_line
    """
    soup = BeautifulSoup(html, "lxml")
    h1 = soup.select_one("h1.doc_header__name")
    headline = h1.get_text(" ", strip=True) if h1 else "Коммерсантъ"
    pub = ""
    t = soup.select_one("time[datetime]")
    if t:
        pub = t.get("datetime") or t.get_text(" ", strip=True)

    profiles: list[dict] = []
    industry = ""

    for table in soup.select("table.innertable"):
        thead = table.find("thead")
        if not thead:
            continue
        headers = [th.get_text(" ", strip=True).lower() for th in thead.find_all("th")]
        if len(headers) < 4 or "фио" not in "".join(headers):
            continue
        tbody = table.find("tbody")
        if not tbody:
            continue
        for tr in tbody.find_all("tr"):
            tds = tr.find_all("td", recursive=False)
            if len(tds) == 1 and str(tds[0].get("colspan") or "").strip() in ("4",):
                b = tds[0].find("b")
                if b:
                    industry = b.get_text(" ", strip=True)
                continue
            if len(tds) != 4:
                continue
            cells = [td.get_text(" ", strip=True) for td in tds]
            c0, c1, c2, c3 = cells
            if c1.lower() == "фио" or c0.lower() == "место":
                continue
            colspan0 = str(tds[0].get("colspan") or "").strip()
            if colspan0 == "4":
                b = tds[0].find("b")
                if b:
                    industry = b.get_text(" ", strip=True)
                continue
            if not c1 or len(c2) < 2 or len(c3) < 1:
                continue
            name = re.sub(r"\s*\*+\s*$", "", c1).strip()
            parts = name.split()
            if len(parts) < 2 or not _FIO_RE.match(name):
                continue
            rank = c0.strip() or "—"
            line = " · ".join(x for x in (industry, rank, name, c2, c3) if x and x != "—")
            profiles.append(
                {
                    "name": name,
                    "role": c2,
                    "company": c3,
                    "industry": industry,
                    "rank": rank,
                    "source_line": line,
                }
            )
    return headline, pub, profiles


def profiles_to_leads(
    profiles: list[dict],
    *,
    article_url: str,
    headline: str,
    published: str,
) -> list[TenderLead]:
    doc_id = _doc_id_from_url(article_url)
    leads: list[TenderLead] = []
    for row in profiles:
        name = row["name"]
        company = row["company"]
        role = row["role"]
        industry = row.get("industry") or ""
        url = _stable_person_url(article_url, name, company)
        li_url = linkedin_people_search_url(name, company)
        ya_url = yandex_people_search_url(name, company)
        title = normalize_person_title(name, role, company)
        snippet = row.get("source_line", "")
        contacts = [
            Contact(
                name=name,
                role=role,
                organization=company,
                email=None,
                phone=None,
                linkedin_search_url=li_url,
                yandex_search_url=ya_url,
                source_snippet=snippet[:400],
            )
        ]
        leads.append(
            TenderLead(
                source="kommersant",
                channel="open_media",
                external_id=doc_id,
                url=url,
                title=title,
                status=TenderStatus.UNKNOWN,
                customer_name=company,
                publish_date=published[:32] if published else None,
                description_snippet=snippet[:500],
                matched_keyword=industry or headline[:120],
                contacts=contacts,
                context_url=article_url,
                context_title=headline,
                raw_extract={
                    "channel_kind": "kommersant_ranking_table",
                    "industry": industry,
                    "rank": row.get("rank"),
                },
                segment=LeadSegment.HR,
            )
        )
    return leads


def normalize_person_title(name: str, role: str, company: str) -> str:
    return f"{name} — {role}, {company}"


async def fetch_html(url: str) -> str:
    async with httpx.AsyncClient(headers=HEADERS, timeout=45.0, follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.text


async def ingest_kommersant_doc(url: str) -> list[TenderLead]:
    host = urlparse(url).netloc.lower()
    if "kommersant.ru" not in host or "/doc/" not in url:
        raise ValueError("Ожидается URL вида https://www.kommersant.ru/doc/…")
    html = await fetch_html(url)
    headline, pub, profiles = parse_kommersant_ranking_html(html, article_url=url)
    if not profiles:
        raise ValueError(
            "В ответе сайта нет таблицы рейтинга (колонки «Место / ФИО / Должность / Компания»). "
            "Часто Kommersant отдаёт «лёгкую» страницу без таблицы (бот, регион). "
            "Сохраните страницу в браузере (Ctrl+S) и импортируйте файл: "
            f'tender-leads open ingest "{url}" --html-file путь/к/page.html'
        )
    return profiles_to_leads(profiles, article_url=url, headline=headline, published=pub)


def parse_kommersant_from_html_file(path: str, *, article_url: str) -> list[TenderLead]:
    """Для тестов / офлайн: разбор сохранённого HTML."""
    with open(path, encoding="utf-8", errors="replace") as f:
        html = f.read()
    headline, pub, profiles = parse_kommersant_ranking_html(html, article_url=article_url)
    if not profiles:
        raise ValueError(
            "В сохранённом файле нет таблицы с ФИО/должность/компания. "
            "Убедитесь, что сохранили полную страницу (не «только HTML» без таблицы)."
        )
    return profiles_to_leads(profiles, article_url=article_url, headline=headline, published=pub)
