"""Агент: поиск по ФИО/компании → обход выдачи → упоминания, выступления, контакты в карточку."""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from tender_agents.agents.profile_enrich_agent import (
    EMAIL_RE,
    HEADERS,
    LINKEDIN_RE,
    PHONE_RE,
    fetch_search_html,
)
from tender_agents.contacts_db import ResearchFindingInput
from tender_agents.text_utils import (
    is_plausible_contact_email,
    is_plausible_contact_phone,
    name_likely_in_text,
    org_latin_slug,
    person_name_tokens,
)

logger = logging.getLogger(__name__)

MAX_SERP_HITS = 14
MAX_PAGE_FETCH = 8
PAGE_DELAY_SEC = 0.7

# Только поисковики — не целевые сайты (LinkedIn/VK/сайт компании разрешены)
SKIP_NETLOCS = {
    "duckduckgo.com",
    "html.duckduckgo.com",
    "lite.duckduckgo.com",
    "yandex.ru",
    "ya.ru",
    "google.com",
    "bing.com",
    "search.brave.com",
    "brave.com",
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "x.com",
}

CAPTCHA_MARKERS = (
    "showcaptcha",
    "captcha",
    "checkbox-captcha",
    "not a robot",
    "подтвердите, что запросы",
)

DATE_RE = re.compile(
    r"(?:\b(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})\b)|"
    r"(?:\b(\d{1,2})[./](\d{1,2})[./](20\d{2})\b)"
)
TG_RE = re.compile(r"(?:https?://)?t\.me/[a-zA-Z0-9_]{4,32}", re.I)
VK_RE = re.compile(r"https?://(?:www\.)?vk\.com/[a-zA-Z0-9_./-]{3,}", re.I)


@dataclass
class SerpHit:
    url: str
    title: str
    snippet: str
    score: int = 0


@dataclass
class ResearchReport:
    query: str
    serp_count: int = 0
    pages_fetched: int = 0
    findings_added: int = 0
    findings_skipped: int = 0
    channels_updated: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    serp_source: str = ""
    needs_captcha: bool = False
    captcha_url: str = ""
    captcha_engine: str = ""


def build_research_queries(full_name: str, organization: str, position: str | None) -> list[str]:
    """Как в ручном поиске: ФИО + компания + контакт/email."""
    base = " ".join(
        p
        for p in (full_name.strip(), organization.strip())
        if p
    )
    queries = [
        f"{base} контакт email",
        base,
    ]
    if position and position.strip():
        short = f"{full_name.strip()} {organization.strip()} контакт"
        if short not in queries:
            queries.append(short)
    out: list[str] = []
    seen: set[str] = set()
    for q in queries:
        q = re.sub(r"\s+", " ", q).strip()
        if q and q not in seen:
            seen.add(q)
            out.append(q)
    return out


def build_research_query(full_name: str, organization: str, position: str | None) -> str:
    return build_research_queries(full_name, organization, position)[0]


def guess_org_seed_hits(organization: str) -> list[SerpHit]:
    """Если выдача недоступна (капча) — типовые URL: сайт /contact, LinkedIn company."""
    slug = org_latin_slug(organization)
    if not slug:
        return []
    hits: list[SerpHit] = []
    seen: set[str] = set()

    def add(url: str, title: str, score: int) -> None:
        if url not in seen:
            seen.add(url)
            hits.append(SerpHit(url=url, title=title, snippet="", score=score))

    for host in (f"https://{slug}.ru", f"https://www.{slug}.ru"):
        add(f"{host}/ru/contact/", f"Контакты — {organization}", 90)
        add(f"{host}/contact/", f"Контакты — {organization}", 85)
    add(f"https://www.linkedin.com/company/{slug}/", f"LinkedIn — {organization}", 70)
    return hits


def _is_blocked_serp(html: str) -> bool:
    low = (html or "").lower()
    if len(html) < 2500 and "captcha" in low:
        return True
    return any(m in low for m in CAPTCHA_MARKERS)


def _normalize_url(href: str, base: str) -> str | None:
    if not href or href.startswith("#") or href.startswith("javascript:"):
        return None
    url = urljoin(base, href).split("#")[0].strip()
    if not url.startswith("http"):
        return None
    try:
        p = urlparse(url)
    except Exception:
        return None
    host = p.netloc.lower().replace("www.", "")
    if host in SKIP_NETLOCS:
        return None
    if any(url.lower().endswith(ext) for ext in (".pdf", ".zip", ".doc", ".docx", ".jpg", ".png")):
        return None
    return url


def _classify_appearance(title: str, snippet: str, url: str) -> str:
    blob = f"{title} {snippet} {url}".lower()
    if "linkedin.com" in blob:
        return "web_profile"
    if "/contact" in blob or "контакт" in blob:
        return "web_contact"
    if "vk.com" in blob:
        return "web_mention"
    if re.search(r"(выступлен|доклад|спикер|конференц|форум|summit|панельн)", blob):
        return "web_speech"
    if re.search(r"(интервью|беседа|подкаст|разговор с)", blob):
        return "web_interview"
    if re.search(r"(рейтинг|топ[\s\-]?\d|топ-\d|список директор)", blob):
        return "web_rating"
    if re.search(r"(hh\.ru|headhunter|работа в|ваканс)", blob):
        return "web_profile"
    return "web_mention"


def _score_link(url: str, title: str, *, org_slug: str | None, name_tokens: list[str]) -> int:
    low = f"{url} {title}".lower()
    score = 0
    if org_slug and org_slug in low:
        score += 8
    for t in name_tokens:
        if len(t) > 3 and t in low:
            score += 4
    if re.search(r"/contact|/контакт", low):
        score += 6
    if "linkedin.com/company" in low:
        score += 5
    if "vk.com/wall" in low or "vk.com/" in low:
        score += 3
    if re.search(r"/news/|/press/|/article/", low):
        score += 2
    return score


def _parse_generic_links(
    html: str,
    *,
    org_slug: str | None,
    name_tokens: list[str],
) -> list[SerpHit]:
    soup = BeautifulSoup(html, "lxml")
    hits: list[SerpHit] = []
    seen: set[str] = set()
    for a in soup.select("a[href]"):
        href = a.get("href") or ""
        url = _normalize_url(href, "")
        if not url or url in seen:
            continue
        title = a.get_text(" ", strip=True) or ""
        score = _score_link(url, title, org_slug=org_slug, name_tokens=name_tokens)
        if score < 3:
            continue
        seen.add(url)
        hits.append(SerpHit(url=url, title=title[:300] or url, snippet="", score=score))
    hits.sort(key=lambda h: -h.score)
    return hits[:MAX_SERP_HITS]


def _parse_yandex_serp(html: str) -> list[SerpHit]:
    if _is_blocked_serp(html):
        return []
    soup = BeautifulSoup(html, "lxml")
    hits: list[SerpHit] = []
    seen: set[str] = set()
    for a in soup.select(
        "a.OrganicTitle-Link, a.Link.OrganicTitle-Link, a.organic__url, "
        "a[data-bem*='organic']"
    ):
        href = a.get("href") or ""
        url = _normalize_url(href, "https://yandex.ru")
        if not url or url in seen:
            continue
        title = a.get_text(" ", strip=True)
        if len(title) < 3:
            continue
        seen.add(url)
        hits.append(SerpHit(url=url, title=title[:300], snippet=""))
    if hits:
        return hits[:MAX_SERP_HITS]
    for li in soup.select("li.serp-item, div.Organic, div.organic"):
        a = li.select_one("a[href^='http']")
        if not a:
            continue
        url = _normalize_url(a.get("href"), "https://yandex.ru")
        if not url or url in seen:
            continue
        title = a.get_text(" ", strip=True)
        sn_el = li.select_one(".OrganicTextContentSpan, .text-container, .OrganicText")
        snippet = sn_el.get_text(" ", strip=True)[:500] if sn_el else ""
        seen.add(url)
        hits.append(SerpHit(url=url, title=title[:300], snippet=snippet))
    return hits


def _parse_ddg_serp(html: str) -> list[SerpHit]:
    soup = BeautifulSoup(html, "lxml")
    hits: list[SerpHit] = []
    seen: set[str] = set()
    for block in soup.select("div.result, div.web-result"):
        a = block.select_one("a.result__a, a.result-link")
        if not a:
            continue
        href = a.get("href") or ""
        if "uddg=" in href:
            qs = parse_qs(urlparse(href).query)
            if qs.get("uddg"):
                href = unquote(qs["uddg"][0])
        url = _normalize_url(href, "https://duckduckgo.com")
        if not url or url in seen:
            continue
        title = a.get_text(" ", strip=True)
        sn = block.select_one(".result__snippet, .result-snippet")
        snippet = sn.get_text(" ", strip=True)[:500] if sn else ""
        seen.add(url)
        hits.append(SerpHit(url=url, title=title[:300], snippet=snippet))
    return hits[:MAX_SERP_HITS]


async def _fetch_serp_html(url: str) -> str:
    return await fetch_search_html(url)


async def collect_serp_hits(
    query: str,
    *,
    yandex_search_url: str | None = None,
    organization: str = "",
    full_name: str = "",
) -> tuple[list[SerpHit], str]:
    from urllib.parse import quote_plus

    org_slug = org_latin_slug(organization)
    name_tokens = person_name_tokens(full_name)

    engines: list[tuple[str, str]] = []
    if (yandex_search_url or "").strip():
        engines.append(("yandex_saved", yandex_search_url.strip()))
    engines.extend(
        [
            ("brave", f"https://search.brave.com/search?q={quote_plus(query)}"),
            ("yandex", f"https://yandex.ru/search/?text={quote_plus(query)}&lr=213"),
            ("ddg", f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"),
            ("ddg_lite", f"https://lite.duckduckgo.com/lite/?q={quote_plus(query)}"),
        ]
    )

    all_hits: list[SerpHit] = []
    seen: set[str] = set()
    source_used = ""
    last_captcha: tuple[str, str] | None = None

    for name, u in engines:
        try:
            html = await _fetch_serp_html(u)
            if _is_blocked_serp(html):
                logger.info("serp blocked (%s): %s", name, u[:70])
                last_captcha = (name, u)
                continue
            batch: list[SerpHit] = []
            if "yandex" in name:
                batch = _parse_yandex_serp(html)
            elif "ddg" in name:
                batch = _parse_ddg_serp(html)
            if not batch:
                batch = _parse_generic_links(html, org_slug=org_slug, name_tokens=name_tokens)
            for h in batch:
                if h.url not in seen:
                    seen.add(h.url)
                    all_hits.append(h)
            if batch and not source_used:
                source_used = name
            if len(all_hits) >= MAX_SERP_HITS:
                break
        except Exception as e:
            logger.debug("serp %s: %s", name, e)

    all_hits.sort(key=lambda h: -h.score)
    if not all_hits:
        seeds = guess_org_seed_hits(organization)
        if seeds:
            all_hits = seeds
            source_used = "org_seed"
    captcha = last_captcha if not all_hits and last_captcha else None
    return all_hits[:MAX_SERP_HITS], source_used, captcha


def _extract_main_text(soup: BeautifulSoup) -> str:
    for tag in soup.select("script, style, noscript, nav, footer, header"):
        tag.decompose()
    for sel in ("article", "main", '[role="main"]', ".article", ".post", "#content", ".content"):
        el = soup.select_one(sel)
        if el:
            return el.get_text(" ", strip=True)[:25000]
    return soup.get_text(" ", strip=True)[:25000]


def _extract_date(text: str) -> datetime | None:
    for m in DATE_RE.finditer(text[:8000]):
        g = m.groups()
        try:
            if g[0]:
                return datetime(int(g[0]), int(g[1]), int(g[2]), tzinfo=timezone.utc)
            if g[5]:
                return datetime(int(g[5]), int(g[4]), int(g[3]), tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
    return None


def _extract_contacts_from_text(text: str) -> dict[str, list[str] | str | None]:
    emails: list[str] = []
    phones: list[str] = []
    linkedin: str | None = None
    for m in EMAIL_RE.finditer(text[:80000]):
        e = m.group(0)
        if is_plausible_contact_email(e) and e not in emails:
            emails.append(e)
    for m in PHONE_RE.finditer(text[:80000]):
        p = m.group(0).strip()
        if is_plausible_contact_phone(p) and p not in phones:
            phones.append(p)
    lm = LINKEDIN_RE.search(text[:80000])
    if lm:
        linkedin = lm.group(0).rstrip("/").split("?")[0]
    tg = TG_RE.search(text[:50000])
    vk = VK_RE.search(text[:50000])
    return {
        "emails": emails[:5],
        "phones": phones[:2],
        "linkedin_url": linkedin,
        "telegram": tg.group(0) if tg else None,
        "vk": vk.group(0) if vk else None,
    }


def _snippet_around_name(text: str, full_name: str, *, width: int = 420) -> str:
    low = text.lower()
    for tok in sorted(person_name_tokens(full_name), key=len, reverse=True):
        i = low.find(tok)
        if i >= 0:
            start = max(0, i - width // 2)
            return re.sub(r"\s+", " ", text[start : start + width]).strip()
    return re.sub(r"\s+", " ", text[:width]).strip()


def _is_org_contact_url(url: str) -> bool:
    low = url.lower()
    return bool(re.search(r"/contact|/контакт|/contacts", low))


async def fetch_page_text(url: str) -> tuple[str, str]:
    from tender_agents.research.fetchers import detect_captcha, fetch_url

    fr = await fetch_url(url)
    if fr.captcha:
        raise RuntimeError("captcha")
    if fr.error and not fr.html:
        raise RuntimeError(fr.error)
    html = fr.html
    soup = BeautifulSoup(html, "lxml")
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    og = soup.select_one("meta[property='og:title']")
    if og and og.get("content"):
        title = og["content"].strip() or title
    return title[:400], _extract_main_text(soup)


def serp_to_finding(hit: SerpHit, full_name: str) -> ResearchFindingInput:
    kind = _classify_appearance(hit.title, hit.snippet, hit.url)
    sn = hit.snippet or hit.title
    if not name_likely_in_text(full_name, sn, min_hits=1):
        sn = f"{hit.title}\n{hit.snippet}".strip()
    return ResearchFindingInput(
        source_url=hit.url,
        source_title=hit.title,
        snippet=sn[:2000],
        source_kind=kind,
        appearance_type=kind.replace("web_", ""),
        meta_json={"from": "serp", "score": hit.score},
    )


def page_to_finding(
    url: str,
    page_title: str,
    text: str,
    full_name: str,
    serp: SerpHit | None,
) -> ResearchFindingInput | None:
    org_contact = _is_org_contact_url(url)
    if not org_contact and not name_likely_in_text(full_name, text):
        return None
    title = page_title or (serp.title if serp else url)
    snippet = (
        _snippet_around_name(text, full_name)
        if name_likely_in_text(full_name, text)
        else re.sub(r"\s+", " ", text[:420]).strip()
    )
    kind = _classify_appearance(title, snippet + " " + text[:2000], url)
    contacts = _extract_contacts_from_text(text)
    appeared = _extract_date(text[:12000])
    meta = {**contacts, "from": "page"}
    if serp and serp.snippet:
        meta["serp_snippet"] = serp.snippet[:400]
    return ResearchFindingInput(
        source_url=url,
        source_title=title,
        snippet=snippet,
        source_kind=kind,
        appeared_at=appeared,
        appearance_type=kind.replace("web_", ""),
        meta_json=meta,
    )


async def run_contact_research(
    repo,
    profile_id: int,
    *,
    max_pages: int = MAX_PAGE_FETCH,
    job_id: int | None = None,
) -> ResearchReport:
    cr = repo.contacts_repo()
    p = await cr.get_by_id(profile_id, with_appearances=False)
    if not p or not p.id:
        raise ValueError("Контакт не найден")

    jobs = repo.research_jobs()
    if job_id:
        await jobs.update_job(job_id, status="running")

    queries = build_research_queries(p.full_name, p.organization, p.position)
    report = ResearchReport(query=queries[0])
    serp: list[SerpHit] = []
    seen_urls: set[str] = set()
    source_used = ""
    prov = repo.provenance()

    for q in queries:
        batch, src, captcha = await collect_serp_hits(
            q,
            yandex_search_url=p.yandex_search_url if not serp else None,
            organization=p.organization,
            full_name=p.full_name,
        )
        if captcha and not batch and not serp:
            report.needs_captcha = True
            report.captcha_engine, report.captcha_url = captcha
            if job_id:
                await jobs.update_job(
                    job_id,
                    status="needs_captcha",
                    search_engine=captcha[0],
                    challenge_url=captcha[1],
                    instructions="Откройте ссылку в браузере, пройдите капчу, затем загрузите HTML или вставьте cookies.",
                )
            return report
        if src and not source_used:
            source_used = src
        for h in batch:
            if h.url not in seen_urls:
                seen_urls.add(h.url)
                serp.append(h)
        if len(serp) >= MAX_SERP_HITS:
            break

    serp.sort(key=lambda h: -h.score)
    serp = serp[:MAX_SERP_HITS]
    report.serp_count = len(serp)
    report.serp_source = source_used

    findings: list[ResearchFindingInput] = []
    for hit in serp:
        findings.append(serp_to_finding(hit, p.full_name))

    fetched = 0
    for hit in serp[:max_pages]:
        try:
            page_title, text = await fetch_page_text(hit.url)
            fetched += 1
            pf = page_to_finding(hit.url, page_title, text, p.full_name, hit)
            if pf:
                for i, f in enumerate(findings):
                    if f.source_url == hit.url:
                        findings[i] = pf
                        break
                else:
                    findings.append(pf)
        except Exception as e:
            report.errors.append(f"{hit.url[:60]}: {e}"[:120])
            logger.debug("page fetch %s: %s", hit.url, e)
        await asyncio.sleep(PAGE_DELAY_SEC)

    report.pages_fetched = fetched
    result = await cr.apply_research_findings(profile_id, findings)
    report.findings_added = result["added"]
    report.findings_skipped = result["skipped"]
    report.channels_updated = result.get("channels") or []

    p2 = await cr.get_by_id(profile_id, with_appearances=False)
    if p2 and p2.id:
        if p2.email:
            await prov.record_provenance(p2.id, report.captcha_url or queries[0], "email", p2.email)
        if p2.phone:
            await prov.record_provenance(p2.id, report.captcha_url or queries[0], "phone", p2.phone)

    if job_id:
        await jobs.update_job(
            job_id,
            status="completed",
            result={
                "serp_count": report.serp_count,
                "findings_added": report.findings_added,
                "channels": report.channels_updated,
            },
        )

    note = (
        f"[research] «{queries[0][:70]}»; источник: {source_used or '—'}; "
        f"ссылок: {report.serp_count}; страниц: {report.pages_fetched}; "
        f"записей: {report.findings_added}"
    )
    if report.channels_updated:
        note += "; каналы: " + ", ".join(report.channels_updated)
    await cr.apply_contact_enrichment(profile_id, notes_append=note)
    return report


def report_summary(r: ResearchReport) -> str:
    parts = [
        f"Выдача: {r.serp_count} ссылок",
    ]
    if r.serp_source:
        parts.append(f"источник: {r.serp_source}")
    parts.extend(
        [
            f"обойдено страниц: {r.pages_fetched}",
            f"добавлено в карточку: {r.findings_added}",
        ]
    )
    if r.findings_skipped:
        parts.append(f"пропущено (дубли): {r.findings_skipped}")
    if r.channels_updated:
        parts.append("обновлены поля: " + ", ".join(r.channels_updated))
    if r.needs_captcha:
        parts.append(f"нужна капча ({r.captcha_engine}): откройте страницу и нажмите «Продолжить»")
    elif r.serp_count == 0:
        parts.append(
            "подсказка: Яндекс часто отдаёт капчу боту — проверьте ссылку «Яндекс» вручную или повторите позже"
        )
    if r.errors:
        parts.append(f"ошибки загрузки: {len(r.errors)}")
    return ". ".join(parts) + "."


async def execute_research_job(repo, job_id: int) -> ResearchReport:
    job = await repo.research_jobs().get_job(job_id)
    if not job:
        raise ValueError("job not found")
    try:
        return await run_contact_research(repo, job.profile_id, job_id=job_id)
    except Exception as e:
        await repo.research_jobs().update_job(job_id, status="failed", error=str(e)[:500])
        raise
