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
    raise ValueError(f"Неизвестный парсер: {parser_id}")
