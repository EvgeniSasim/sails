"""Enrich Agent — заходит в карточку тендера и извлекает контакты и реквизиты."""

from __future__ import annotations

import asyncio
import logging

from tender_agents.models import SearchResultItem, TenderLead
from tender_agents.settings import settings
from tender_agents.sources.base import SourceAdapter

logger = logging.getLogger(__name__)


class EnrichAgent:
    def __init__(self, delay_sec: float | None = None):
        self.delay_sec = delay_sec if delay_sec is not None else settings.request_delay_sec

    async def run(
        self,
        items: list[tuple[SourceAdapter, str, SearchResultItem]],
    ) -> list[TenderLead]:
        leads: list[TenderLead] = []
        for adapter, keyword, item in items:
            logger.info("EnrichAgent: %s", item.url)
            try:
                lead = await adapter.enrich(item, keyword)
                leads.append(lead)
            except Exception:
                logger.exception("Enrich failed: %s", item.url)
            await asyncio.sleep(self.delay_sec)
        logger.info("EnrichAgent: обогащено %s карточек", len(leads))
        return leads
