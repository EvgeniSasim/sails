"""Запуск ролей Search / Enrich через агентов Yandex AI Studio."""

from __future__ import annotations

import logging
from typing import Any

from tender_agents.scrape.html_utils import html_to_text_snippet
from tender_agents.settings import settings
from tender_agents.yandex.client import YandexStudioClient
from tender_agents.yandex.prompts import ENRICH_AGENT_INSTRUCTIONS, SEARCH_AGENT_INSTRUCTIONS

logger = logging.getLogger(__name__)


def _load_agent_instructions(role: str, default: str) -> str:
    try:
        import yaml
        from tender_agents.settings import CONFIG_DIR

        path = CONFIG_DIR / "yandex_agents.yaml"
        if path.exists():
            with path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            agents = data.get("agents", {})
            if role in agents and agents[role].get("instructions"):
                return str(agents[role]["instructions"]).strip()
    except Exception:
        logger.debug("yandex_agents.yaml not loaded for role %s", role)
    return default


class YandexAgentRunner:
    """Агенты Yandex для extract_list / extract_detail (HTML → JSON)."""

    def __init__(self, client: YandexStudioClient | None = None):
        self.client = client or YandexStudioClient()
        self.search_instructions = _load_agent_instructions("search", SEARCH_AGENT_INSTRUCTIONS)
        self.enrich_instructions = _load_agent_instructions("enrich", ENRICH_AGENT_INSTRUCTIONS)

    def _web_search_tools(self) -> list[dict[str, Any]] | None:
        if not settings.yandex_enable_web_search:
            return None
        return [{"type": "web_search"}]

    async def extract_list_from_html(
        self,
        html: str,
        *,
        keyword: str,
        source_name: str,
        page_url: str,
    ) -> dict[str, Any]:
        text = html_to_text_snippet(html, max_chars=settings.yandex_max_html_chars)
        user_input = (
            f"Площадка: {source_name}\n"
            f"Ключевое слово: «{keyword}»\n"
            f"URL страницы: {page_url}\n\n"
            f"Текст страницы:\n{text}"
        )
        logger.info("Yandex Search Agent: %s / «%s»", source_name, keyword)
        return await self.client.chat_json(
            instructions=self.search_instructions,
            user_input=user_input,
            tools=self._web_search_tools(),
        )

    async def extract_detail_from_html(
        self,
        html: str,
        *,
        keyword: str,
        page_url: str,
    ) -> dict[str, Any]:
        text = html_to_text_snippet(html, max_chars=settings.yandex_max_html_chars)
        user_input = (
            f"Ключевое слово поиска: «{keyword}»\n"
            f"URL карточки: {page_url}\n\n"
            f"Текст страницы:\n{text}"
        )
        logger.info("Yandex Enrich Agent: %s", page_url)
        return await self.client.chat_json(
            instructions=self.enrich_instructions,
            user_input=user_input,
        )
