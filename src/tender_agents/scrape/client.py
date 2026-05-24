"""ScrapeGraphAI API client — https://scrapegraphai.com/"""

from __future__ import annotations

import json
from typing import Any

import httpx

from tender_agents.settings import settings


class ScrapeGraphClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key or settings.sgai_api_key
        self.base_url = (base_url or settings.scrapegraph_base_url).rstrip("/")

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise ValueError(
                "SGAI_API_KEY не задан. Получите ключ на https://scrapegraphai.com/dashboard"
            )
        return {"Content-Type": "application/json", "SGAI-APIKEY": self.api_key}

    async def extract(self, url: str, prompt: str, *, stealth: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "url": url,
            "prompt": prompt,
        }
        if stealth:
            payload["stealth"] = True

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.base_url}/extract",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return self._normalize_result(data)

    async def scrape_markdown(self, url: str, *, render_js: bool = True) -> str:
        payload: dict[str, Any] = {
            "url": url,
            "formats": [{"type": "markdown"}],
        }
        if render_js:
            payload["renderMode"] = "js"

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.base_url}/scrape",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                return data.get("markdown") or data.get("content") or json.dumps(data)
            return str(data)

    @staticmethod
    def _normalize_result(data: Any) -> dict[str, Any]:
        if isinstance(data, dict):
            if "result" in data and isinstance(data["result"], dict):
                return data["result"]
            if "data" in data and isinstance(data["data"], dict):
                return data["data"]
            return data
        if isinstance(data, str):
            try:
                parsed = json.loads(data)
                return ScrapeGraphClient._normalize_result(parsed)
            except json.JSONDecodeError:
                return {"raw": data}
        return {"raw": data}
