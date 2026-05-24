"""Точка входа: URL → список лидов (диспетчер по домену)."""

from __future__ import annotations

from urllib.parse import urlparse

from tender_agents.models import TenderLead


async def ingest_url(url: str, *, html_file: str | None = None) -> list[TenderLead]:
    from tender_agents.channels.registry import match_parser_id, list_parsers, run_parser

    u = url.strip()
    parser_id = match_parser_id(u)
    if parser_id:
        return await run_parser(parser_id, u, html_file=html_file)
    host = urlparse(u).netloc.lower()
    known = ", ".join(p["hosts"] for p in list_parsers())
    raise ValueError(
        f"Хост не поддержан: {host}. "
        f"Доступные домены: {known}. Добавьте запись в channels/registry.py."
    )
