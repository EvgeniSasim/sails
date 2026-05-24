"""Профили людей → TenderLead (open_media → contact_profiles)."""

from __future__ import annotations

import hashlib

from tender_agents.channels.kommersant import normalize_person_title
from tender_agents.channels.linkedin_hint import linkedin_people_search_url, yandex_people_search_url
from tender_agents.models import Contact, LeadSegment, TenderLead, TenderStatus


def stable_person_url(article_url: str, name: str, company: str) -> str:
    h = hashlib.sha256(f"{article_url}|{name}|{company}".encode()).hexdigest()[:16]
    return f"{article_url.rstrip('/')}#person-{h}"


def profiles_to_leads(
    profiles: list[dict],
    *,
    article_url: str,
    headline: str,
    source: str = "open_media",
    channel_kind: str = "ai_open_media",
) -> list[TenderLead]:
    leads: list[TenderLead] = []
    for row in profiles:
        name = (row.get("name") or "").strip()
        company = (row.get("company") or "").strip() or "—"
        if not name:
            continue
        role = (row.get("role") or "").strip()
        bio = (row.get("bio") or "").strip()
        rank = row.get("rank") or "—"
        url = stable_person_url(article_url, name, company)
        li_url = linkedin_people_search_url(name, company if company != "—" else "")
        ya_url = yandex_people_search_url(name, company if company != "—" else "")
        title = normalize_person_title(name, role or "специалист", company)
        snippet_parts = [x for x in (f"Место {rank}" if rank != "—" else "", company) if x and x != "—"]
        if row.get("score"):
            snippet_parts.append(f"{row['score']} баллов")
        snippet = " · ".join(snippet_parts) or headline[:120]
        contacts = [
            Contact(
                name=name,
                role=role or None,
                organization=company if company != "—" else None,
                email=(row.get("email") or "").strip() or None,
                phone=(row.get("phone") or "").strip() or None,
                linkedin_search_url=li_url,
                yandex_search_url=ya_url,
                source_snippet=snippet[:400],
            )
        ]
        leads.append(
            TenderLead(
                source=source,
                channel="open_media",
                external_id=None,
                url=url,
                title=title,
                status=TenderStatus.UNKNOWN,
                customer_name=company if company != "—" else None,
                description_snippet=bio[:2000] if bio else snippet,
                matched_keyword=headline[:120],
                contacts=contacts,
                context_url=article_url,
                context_title=headline,
                raw_extract={
                    "channel_kind": channel_kind,
                    "rank": rank,
                    "score": row.get("score"),
                    "bio": bio[:8000] if bio else None,
                },
                segment=LeadSegment.HR,
            )
        )
    return leads


def page_title_from_html(html: str) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    h1 = soup.select_one("h1")
    if h1:
        return h1.get_text(" ", strip=True)[:300]
    if soup.title:
        return soup.title.get_text(" ", strip=True)[:300]
    return "Открытый источник"
