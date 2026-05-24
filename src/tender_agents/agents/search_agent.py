"""Search Agent — находит карточки тендеров по ключевым словам на площадках."""

from __future__ import annotations

import asyncio
import logging
from datetime import date

from tender_agents.models import SearchResultItem
from tender_agents.scrape.filters import normalize_url
from tender_agents.settings import settings
from tender_agents.sources.base import SourceAdapter

logger = logging.getLogger(__name__)

# Площадки с нестабильным доступом из РФ / без нативного парсера — без traceback
_SOFT_FAIL_SOURCES = frozenset({"sberbank_ast", "b2b_center", "gosplan"})


class SearchAgent:
    def __init__(self, adapters: list[SourceAdapter], delay_sec: float | None = None):
        self.adapters = adapters
        self.delay_sec = delay_sec if delay_sec is not None else settings.request_delay_sec

    async def run(
        self,
        keywords: list[str],
        *,
        max_per_keyword: int = 20,
        date_from: date | None = None,
        date_to: date | None = None,
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
                    items = await adapter.search(
                        keyword,
                        date_from=date_from,
                        date_to=date_to,
                    )
                except Exception as e:
                    import httpx

                    from tender_agents.yandex.client import YandexStudioError

                    if adapter.source_id in _SOFT_FAIL_SOURCES or isinstance(
                        e,
                        (
                            YandexStudioError,
                            httpx.TimeoutException,
                            httpx.ConnectError,
                            httpx.NetworkError,
                        ),
                    ) or type(e).__module__.startswith("playwright"):
                        logger.warning(
                            "Search skipped %s / «%s»: %s",
                            adapter.source_id,
                            keyword,
                            e,
                        )
                    elif isinstance(e, ImportError) and "playwright" in str(e).lower():
                        logger.warning(
                            "Search skipped %s / «%s»: %s — "
                            "установите playwright или выберите бэкенд httpx в Настройки → Проект",
                            adapter.source_id,
                            keyword,
                            e,
                        )
                    else:
                        logger.exception(
                            "Search failed: %s / %s", adapter.source_id, keyword
                        )
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
