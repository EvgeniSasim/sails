"""Crawl4AI — бесплатный OSS, LLM через Ollama (локально, без облака)."""

from __future__ import annotations

import json
from typing import Any

from tender_agents.scrape.base import ExtractBackend
from tender_agents.scrape.prompts import TENDER_DETAIL_PROMPT, TENDER_LIST_PROMPT
from tender_agents.settings import settings


class Crawl4AIBackend(ExtractBackend):
    name = "crawl4ai"

    async def extract_list(self, url: str, *, keyword: str, source_name: str) -> dict[str, Any]:
        instruction = (
            f"{TENDER_LIST_PROMPT} Ключ: «{keyword}». Площадка: {source_name}. "
            "Ответ строго JSON."
        )
        return await self._run_llm_extraction(url, instruction)

    async def extract_detail(self, url: str, *, keyword: str) -> dict[str, Any]:
        instruction = f"{TENDER_DETAIL_PROMPT} Запрос: «{keyword}». Ответ строго JSON."
        return await self._run_llm_extraction(url, instruction)

    async def _run_llm_extraction(self, url: str, instruction: str) -> dict[str, Any]:
        try:
            from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, LLMConfig
            from crawl4ai.extraction_strategy import LLMExtractionStrategy
        except ImportError as e:
            raise ImportError(
                "Установите: pip install -e '.[crawl4ai]' и запустите Ollama (ollama pull llama3.2)"
            ) from e

        provider = settings.ollama_model
        llm_config = LLMConfig(
            provider=f"ollama/{provider}",
            api_token=None,
            base_url=settings.ollama_base_url,
        )
        strategy = LLMExtractionStrategy(
            llm_config=llm_config,
            instruction=instruction,
            schema=None,
        )
        browser_cfg = BrowserConfig(headless=True)
        run_cfg = CrawlerRunConfig(extraction_strategy=strategy, word_count_threshold=10)

        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            result = await crawler.arun(url=url, config=run_cfg)
            if not result.success:
                raise RuntimeError(result.error_message or "crawl4ai failed")
            raw = result.extracted_content
            if isinstance(raw, str):
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return {"raw": raw, "items": []}
            if isinstance(raw, list) and raw:
                return raw[0] if isinstance(raw[0], dict) else {"items": raw}
            return raw if isinstance(raw, dict) else {"items": []}
