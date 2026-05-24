"""Search Agent — находит карточки тендеров по ключевым словам на площадках."""

from __future__ import annotations

import asyncio
import logging

from tender_agents.models import SearchResultItem
from tender_agents.scrape.filters import normalize_url
from tender_agents.settings import settings
from tender_agents.sources.base import SourceAdapter

logger = logging.getLogger(__name__)


class SearchAgent:
    def __init__(self, adapters: list[SourceAdapter], delay_sec: float | None = None):
        self.adapters = adapters
        self.delay_sec = delay_sec if delay_sec is not None else settings.request_delay_sec

    async def run(
        self,
        keywords: list[str],
        *,
        max_per_keyword: int = 20,
    ) -> list[tuple[SourceAdapter, str, SearchResultItem]]:
        """Возвращает (adapter, keyword, item) для каждой найденной карточки."""
        results: list[tuple[SourceAdapter, str, SearchResultItem]] = []
        seen_urls: set[str] = set()

        for adapter in self.adapters:
            for keyword in keywords:
                logger.info(
                    "SearchAgent: %s — «%s»",
                    adapter.config.get("name", adapter.source_id),
                    keyword,
                )
                try:
                    items = await adapter.search(keyword)
                except Exception:
                    logger.exception("Search failed: %s / %s", adapter.source_id, keyword)
                    await asyncio.sleep(self.delay_sec)
                    continue

                for item in items[:max_per_keyword]:
                    url_key = normalize_url(item.url)
                    if url_key in seen_urls:
                        continue
                    seen_urls.add(url_key)
                    results.append((adapter, keyword, item))

                await asyncio.sleep(self.delay_sec)

        logger.info("SearchAgent: найдено %s уникальных URL", len(results))
        return results
