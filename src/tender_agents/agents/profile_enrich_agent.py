"""Обогащение контактов из открытой выдачи поиска (Яндекс / DuckDuckGo HTML)."""

from __future__ import annotations

import asyncio
import logging
import re
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from tender_agents.text_utils import is_plausible_contact_email, is_plausible_contact_phone

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.5",
    "Referer": "https://yandex.ru/",
}

LINKEDIN_RE = re.compile(
    r"https?://(?:[a-z]{2,3}\.)?linkedin\.com/in/[a-zA-Z0-9\-_%]+/?", re.I
)
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
# Мобильный РФ: +7 9xx …
PHONE_RE = re.compile(
    r"(?:\+7|8)[\s\-]?\(?9\d{2}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}"
)

_DDG_JUNK_MARKERS = (
    "error-lite@duckduckgo.com",
    "duckduckgo.com/lite",
    "anomaly-modal",
)


def _is_search_engine_error_page(html: str) -> bool:
    low = (html or "").lower()
    return any(m in low for m in _DDG_JUNK_MARKERS)


def _serp_text(html: str) -> str:
    """Текст сниппетов выдачи — без футера/скриптов поисковика."""
    soup = BeautifulSoup(html or "", "lxml")
    for tag in soup.select("script, style, noscript, footer, nav"):
        tag.decompose()
    chunks: list[str] = []
    for sel in (
        ".result__snippet",
        ".result__body",
        ".OrganicText",
        ".OrganicTitle",
        ".serp-item__text",
        ".Path-Item",
    ):
        for el in soup.select(sel):
            t = el.get_text(" ", strip=True)
            if t and len(t) > 8:
                chunks.append(t)
    if chunks:
        return "\n".join(chunks)
    return soup.get_text(" ", strip=True)[:120000]


async def fetch_search_html(url: str) -> str:
    async with httpx.AsyncClient(headers=HEADERS, timeout=40.0, follow_redirects=True) as c:
        r = await c.get(url)
        r.raise_for_status()
        return r.text


def pick_linkedin_url(html: str, full_name: str) -> str | None:
    text = html or ""
    for m in LINKEDIN_RE.finditer(text):
        u = m.group(0).rstrip("/").split("?")[0]
        if "/in/" not in u.lower():
            continue
        parts = (full_name or "").lower().split()
        if len(parts) >= 1:
            hint = re.sub(r"[^a-zа-яё0-9]", "", parts[0])[:10]
            slug = u.lower().split("/in/")[-1]
            if hint and hint in re.sub(r"[^a-zа-яё0-9]", "", slug):
                return u
    m = LINKEDIN_RE.search(text)
    return m.group(0).rstrip("/").split("?")[0] if m else None


def pick_email(text: str) -> str | None:
    for m in EMAIL_RE.finditer(text[:200000]):
        cand = m.group(0)
        if is_plausible_contact_email(cand):
            return cand
    return None


def pick_phone(text: str) -> str | None:
    flat = (text or "").replace("\xa0", " ")
    for m in PHONE_RE.finditer(flat[:200000]):
        cand = m.group(0).replace("  ", " ").strip()
        if is_plausible_contact_phone(cand):
            return cand
    return None


def _filter_found(found: dict[str, str | None]) -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for k, v in found.items():
        if not v:
            continue
        if k == "linkedin_url" and "linkedin.com/in" in v.lower():
            out[k] = v
        elif k == "email" and is_plausible_contact_email(v):
            out[k] = v
        elif k == "phone" and is_plausible_contact_phone(v):
            out[k] = v
    return out


async def enrich_contact_from_web(
    *,
    full_name: str,
    organization: str,
    yandex_search_url: str | None,
) -> dict[str, str | None]:
    """Собрать кандидатов linkedin / email / phone из HTML выдачи (ничего не пишет в БД)."""
    out: dict[str, str | None] = {}
    q = f"{full_name} {organization} linkedin".strip()
    urls: list[str] = []
    if (yandex_search_url or "").strip():
        urls.append(yandex_search_url.strip())
    urls.append(f"https://html.duckduckgo.com/html/?q={quote_plus(q)}")

    html = ""
    last_err: Exception | None = None
    for u in urls:
        try:
            html = await fetch_search_html(u)
            if _is_search_engine_error_page(html) and "yandex" not in u.lower():
                logger.info("skip junk search page: %s", u[:80])
                continue
            if "linkedin.com/in" in html.lower():
                break
            soup = BeautifulSoup(html, "lxml")
            if soup.select("a.result__a") or soup.select(".OrganicTitle"):
                break
        except Exception as e:
            last_err = e
            logger.debug("search fetch failed %s: %s", u, e)
            continue
    if not html or _is_search_engine_error_page(html):
        if last_err:
            raise last_err
        raise ValueError(
            "Поиск вернул служебную страницу (DuckDuckGo/блокировка). "
            "Откройте ссылку «Яндекс» в карточке вручную или повторите позже."
        )

    serp = _serp_text(html)
    li = pick_linkedin_url(html, full_name)
    if li:
        out["linkedin_url"] = li
    em = pick_email(serp)
    if em:
        out["email"] = em
    ph = pick_phone(serp)
    if ph:
        out["phone"] = ph
    return _filter_found(out)


async def enrich_contact_profile(repo, profile_id: int) -> dict[str, str | None]:
    """Один контакт: поиск → запись в contact_profiles."""
    cr = repo.contacts_repo()
    p = await cr.get_by_id(profile_id, with_appearances=False)
    if not p or not p.id:
        raise ValueError("Контакт не найден")
    found = await enrich_contact_from_web(
        full_name=p.full_name,
        organization=p.organization,
        yandex_search_url=p.yandex_search_url or p.linkedin_search_url,
    )
    if not found:
        await cr.apply_contact_enrichment(
            profile_id,
            notes_append="[enrich] в сниппетах выдачи нет проверенных e-mail/тел./LinkedIn",
        )
        return found
    note_bits = [k for k in found if found[k]]
    note = "[enrich] " + ", ".join(note_bits) if note_bits else "[enrich] пусто"
    await cr.apply_contact_enrichment(
        profile_id,
        linkedin_url=found.get("linkedin_url"),
        email=found.get("email"),
        phone=found.get("phone"),
        notes_append=note,
    )
    return found


async def enrich_contacts_batch(repo, *, limit: int = 12) -> int:
    """Пакетно: контакты без linkedin_url, с паузой между запросами."""
    cr = repo.contacts_repo()
    profiles = await cr.list_profiles_needing_enrichment(limit)
    n = 0
    for p in profiles:
        if not p.id:
            continue
        try:
            await enrich_contact_profile(repo, p.id)
            n += 1
        except Exception:
            logger.exception("enrich profile %s", p.id)
        await asyncio.sleep(0.85)
    return n
