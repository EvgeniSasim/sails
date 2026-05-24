"""Точка входа: любой URL → контакты (нативный парсер или ИИ)."""

from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import urlparse

from tender_agents.channels.page_fetch import fetch_page_html
from tender_agents.channels.people_leads import page_title_from_html, profiles_to_leads
from tender_agents.models import TenderLead

logger = logging.getLogger(__name__)


def _native_profiles_from_html(parser_id: str, html: str, *, article_url: str) -> tuple[str, list[dict]]:
    if parser_id == "kommersant":
        from tender_agents.channels.kommersant import parse_kommersant_ranking_html

        headline, pub, profiles_raw = parse_kommersant_ranking_html(html, article_url=article_url)
        profiles = [
            {
                "name": p["name"],
                "company": p["company"],
                "role": p.get("role") or "",
                "rank": p.get("rank") or "—",
                "bio": p.get("source_line") or "",
            }
            for p in profiles_raw
        ]
        return headline or pub or page_title_from_html(html), profiles

    if parser_id == "hr_ratings":
        from tender_agents.channels.hr_ratings import parse_hr_ratings_html

        headline, profiles = parse_hr_ratings_html(html, article_url=article_url)
        return headline, profiles

    return page_title_from_html(html), []


async def ingest_url(url: str, *, html_file: str | None = None) -> list[TenderLead]:
    """
    Импорт ЛПР с любого URL.

    1. Загрузка HTML (httpx → Playwright при блокировке).
    2. Быстрый нативный парсер для известных доменов (kommersant, hr-ratings).
    3. Иначе или если мало профилей — YandexGPT извлекает всех людей из текста.
    4. Дедупликация при сохранении — в contacts_db.upsert_open_media_batch.
    """
    from tender_agents.channels.registry import match_parser_id
    from tender_agents.channels.open_media_ai import extract_people_with_ai
    from tender_agents.yandex.config import is_yandex_configured

    u = url.strip()
    if not u.startswith("http"):
        raise ValueError("Нужен полный URL (https://…)")

    if html_file:
        p = Path(html_file).expanduser()
        if not p.is_file():
            raise ValueError(f"Файл не найден: {p}")
        html = p.read_text(encoding="utf-8", errors="replace")
    else:
        html = await fetch_page_html(u)

    headline = page_title_from_html(html)
    parser_id = match_parser_id(u)
    profiles: list[dict] = []
    channel_kind = "ai_open_media"
    source = "open_media"

    from tender_agents.channels.listing_extract import try_extract_listing_with_pagination

    if html_file:
        from tender_agents.channels.listing_extract import try_extract_listing

        listing_profiles = try_extract_listing(html, page_url=u)
    else:
        listing_profiles = await try_extract_listing_with_pagination(
            u, html_first=html, fetch_html=fetch_page_html
        )
    if listing_profiles:
        profiles = listing_profiles
        channel_kind = "listing_catalog"
        source = "open_media"
        logger.info("Catalog listing: %s профилей с %s", len(profiles), u[:80])

    if parser_id and not profiles:
        try:
            headline, profiles = _native_profiles_from_html(parser_id, html, article_url=u)
            if profiles:
                channel_kind = parser_id
                source = parser_id
                logger.info("Native parser %s: %s профилей", parser_id, len(profiles))
        except Exception as e:
            logger.warning("Native parser %s skipped: %s", parser_id, e)
            profiles = []

    if len(profiles) < 1:
        if not is_yandex_configured():
            host = urlparse(u).netloc.lower()
            raise ValueError(
                f"Для URL {host} нужен агент извлечения ЛПР (YandexGPT). "
                "Задайте YANDEX_API_KEY и YANDEX_FOLDER_ID в Настройки → API, "
                "либо сохраните страницу в браузере и импортируйте файл HTML."
            )
        profiles, summary = await extract_people_with_ai(
            html, page_url=u, page_title=headline
        )
        if summary:
            headline = summary[:300] or headline
        channel_kind = "ai_open_media"
        source = "open_media"
        logger.info("AI open_media extract: %s профилей с %s", len(profiles), u[:80])

    if not profiles:
        raise ValueError(
            "На странице не найдено людей (ФИО + контекст). "
            "Проверьте URL или сохраните полную страницу и импортируйте: "
            f'tender-leads open ingest "{u}" --html-file page.html'
        )

    return profiles_to_leads(
        profiles,
        article_url=u,
        headline=headline,
        source=source,
        channel_kind=channel_kind,
    )
