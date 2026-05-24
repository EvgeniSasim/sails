"""Реестр парсеров открытых каналов (СМИ, рейтинги) по домену."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable
from urllib.parse import urlparse

from tender_agents.models import TenderLead


@dataclass(frozen=True)
class ChannelParserEntry:
    id: str
    hosts: tuple[str, ...]
    description: str


REGISTRY: tuple[ChannelParserEntry, ...] = (
    ChannelParserEntry(
        id="kommersant",
        hosts=("kommersant.ru",),
        description="Таблицы рейтингов / ФИО на kommersant.ru",
    ),
    ChannelParserEntry(
        id="hr_ratings",
        hosts=("hr-ratings.com",),
        description="Рейтинги HR-директоров (Tilda), карточки ЛПР с bio",
    ),
)


def match_parser_id(url: str) -> str | None:
    host = urlparse(url.strip()).netloc.lower()
    for entry in REGISTRY:
        if any(h in host for h in entry.hosts):
            return entry.id
    return None


def list_parsers() -> list[dict[str, str]]:
    return [
        {"id": e.id, "hosts": ", ".join(e.hosts), "description": e.description}
        for e in REGISTRY
    ]


async def run_parser(parser_id: str, url: str, *, html_file: str | None = None) -> list[TenderLead]:
    if parser_id == "kommersant":
        from tender_agents.channels import kommersant as k

        if html_file:
            from pathlib import Path

            p = Path(html_file).expanduser()
            if not p.is_file():
                raise ValueError(f"Файл не найден: {p}")
            return k.parse_kommersant_from_html_file(str(p), article_url=url)
        return await k.ingest_kommersant_doc(url)
    if parser_id == "hr_ratings":
        from tender_agents.channels import hr_ratings as hr

        if html_file:
            from pathlib import Path

            p = Path(html_file).expanduser()
            if not p.is_file():
                raise ValueError(f"Файл не найден: {p}")
            html = p.read_text(encoding="utf-8", errors="replace")
            headline, profiles = hr.parse_hr_ratings_html(html, article_url=url)
            if not profiles:
                raise ValueError("В файле не найдены участники рейтинга (h2 «N. ФИО, Компания»).")
            from tender_agents.channels.people_leads import profiles_to_leads

            return profiles_to_leads(
                profiles,
                article_url=url,
                headline=headline,
                source="hr_ratings",
                channel_kind="hr_ratings",
            )
        return await hr.ingest_hr_ratings_url(url)
    raise ValueError(f"Неизвестный парсер: {parser_id}")
