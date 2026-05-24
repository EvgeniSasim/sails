"""Orchestrator — координирует Search → Enrich → Store."""

from __future__ import annotations

import logging

from tender_agents.agents.enrich_agent import EnrichAgent
from tender_agents.agents.search_agent import SearchAgent
from tender_agents.agents.store_agent import StoreAgent
from tender_agents.config_loader import load_keywords, load_sources
from tender_agents.db import LeadRepository, create_repository
from tender_agents.settings import settings
from tender_agents.scrape.base import ExtractBackend
from tender_agents.scrape.factory import get_backend
from tender_agents.sources import build_adapters

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(
        self,
        *,
        keywords: list[str] | None = None,
        source_ids: list[str] | None = None,
        backend: ExtractBackend | None = None,
        agent_provider: str | None = None,
        repo: LeadRepository | None = None,
    ):
        self.keywords = keywords or load_keywords()
        sources_cfg = load_sources()
        if source_ids:
            sources_cfg = {k: v for k, v in sources_cfg.items() if k in source_ids}
        provider = (agent_provider or settings.agent_provider).lower()
        if provider == "yandex" and backend is None:
            backend = get_backend("yandex")
        self.agent_provider = provider
        self.backend = backend or get_backend()
        self.adapters = build_adapters(sources_cfg, self.backend)
        self.repo = repo or create_repository()
        self.search_agent = SearchAgent(self.adapters)
        self.enrich_agent = EnrichAgent()
        self.store_agent = StoreAgent(self.repo)

    async def run_pipeline(
        self,
        *,
        max_per_keyword: int = 10,
        skip_enrich: bool = False,
    ) -> dict:
        await self.repo.init()

        plan_notes = None
        if self.agent_provider == "yandex":
            plan_notes = await self._yandex_plan()

        found = await self.search_agent.run(
            self.keywords,
            max_per_keyword=max_per_keyword,
        )

        if skip_enrich:
            from tender_agents.models import Contact, TenderLead, TenderStatus

            leads = [
                TenderLead(
                    source=adapter.source_id,
                    external_id=item.external_id,
                    title=item.title,
                    url=item.url,
                    status=TenderStatus.UNKNOWN,
                    customer_name=item.customer_hint,
                    matched_keyword=keyword,
                    contacts=[],
                )
                for adapter, keyword, item in found
            ]
        else:
            leads = await self.enrich_agent.run(found)

        count = await self.store_agent.run(leads)
        result = {
            "keywords": len(self.keywords),
            "sources": len(self.adapters),
            "found_urls": len(found),
            "stored": count,
            "agent_provider": self.agent_provider,
            "backend": self.backend.name,
        }
        if plan_notes:
            result["yandex_plan"] = plan_notes
        return result

    async def _yandex_plan(self) -> dict | None:
        try:
            from tender_agents.yandex.client import YandexStudioClient
            from tender_agents.yandex.prompts import ORCHESTRATOR_INSTRUCTIONS

            client = YandexStudioClient()
            sources = [a.source_id for a in self.adapters]
            user_input = (
                f"Ключевые слова: {', '.join(self.keywords[:5])}\n"
                f"Площадки: {', '.join(sources)}"
            )
            instructions = ORCHESTRATOR_INSTRUCTIONS
            try:
                import yaml
                from tender_agents.settings import CONFIG_DIR

                path = CONFIG_DIR / "yandex_agents.yaml"
                if path.exists():
                    with path.open(encoding="utf-8") as f:
                        data = yaml.safe_load(f) or {}
                    instructions = (
                        data.get("agents", {}).get("orchestrator", {}).get("instructions")
                        or instructions
                    )
            except Exception:
                pass
            plan = await client.chat_json(instructions=instructions, user_input=user_input)
            logger.info("Yandex orchestrator plan: %s", plan)
            return plan
        except Exception:
            logger.exception("Yandex orchestrator plan skipped")
            return None
