"""Точка входа: URL → список лидов (диспетчер по домену)."""

from __future__ import annotations

from urllib.parse import urlparse

from tender_agents.models import TenderLead


async def ingest_url(url: str, *, html_file: str | None = None) -> list[TenderLead]:
    u = url.strip()
    host = urlparse(u).netloc.lower()
    if "kommersant.ru" in host:
        from pathlib import Path

        from tender_agents.channels import kommersant as k

        if html_file:
            p = Path(html_file).expanduser()
            if not p.is_file():
                raise ValueError(f"Файл не найден: {p}")
            return k.parse_kommersant_from_html_file(str(p), article_url=u)
        return await k.ingest_kommersant_doc(u)
    raise ValueError(
        f"Хост не поддержан: {host}. "
        "Сейчас: kommersant.ru (таблицы рейтингов). Добавьте парсер в channels/ingest.py."
    )
