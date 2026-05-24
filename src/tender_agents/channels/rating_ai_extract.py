"""Обратная совместимость — см. open_media_ai."""

from __future__ import annotations

from tender_agents.channels.open_media_ai import (
    extract_people_with_ai as _extract_people_with_ai,
    html_to_extract_text,
)


async def extract_people_with_ai(
    html: str,
    *,
    page_url: str,
    page_title: str = "",
) -> list[dict]:
    profiles, _summary = await _extract_people_with_ai(
        html, page_url=page_url, page_title=page_title
    )
    return profiles
