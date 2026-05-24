"""Playwright — бесплатно, нужен Chromium: playwright install chromium."""

from __future__ import annotations

from typing import Any

from tender_agents.scrape.backends.httpx_llm_free import HttpxFreeBackend


class PlaywrightBackend(HttpxFreeBackend):
    name = "playwright"

    async def _fetch(self, url: str) -> str:
        try:
            from playwright.async_api import async_playwright
        except ImportError as e:
            raise ImportError(
                "Установите: pip install -e '.[playwright]' && playwright install chromium"
            ) from e

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(
                user_agent="Mozilla/5.0 (compatible; TenderLeadAgents/0.1)"
            )
            await page.goto(url, wait_until="networkidle", timeout=90_000)
            html = await page.content()
            await browser.close()
        return html
