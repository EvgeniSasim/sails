"""ГосПлан API v2 — JSON без скрапинга (тест: v2test.gosplan.info)."""

from __future__ import annotations

from urllib.parse import quote_plus, urljoin

import httpx

from tender_agents.models import SearchResultItem, TenderLead
from tender_agents.settings import settings
from tender_agents.sources.base import SourceAdapter


class GosplanAdapter(SourceAdapter):
    source_id = "gosplan"

    def build_search_url(self, keyword: str) -> str:
        return f"{self.base_url}/fz44/purchases?search={quote_plus(keyword)}"

    async def search(self, keyword: str) -> list[SearchResultItem]:
        base = settings.gosplan_api_url.rstrip("/")
        headers = {}
        if settings.gosplan_api_key:
            headers["Authorization"] = f"Bearer {settings.gosplan_api_key}"

        items: list[SearchResultItem] = []
        async with httpx.AsyncClient(timeout=60.0, headers=headers) as client:
            # Публичный тестовый эндпоинт; точный path см. swagger.gosplan.info
            for path in (
                f"/fz44/purchases?limit=20&search={quote_plus(keyword)}",
                f"/purchases?limit=20&q={quote_plus(keyword)}",
            ):
                url = f"{base}{path}"
                try:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        continue
                    data = resp.json()
                    items = self._parse_api_list(data, base)
                    if items:
                        break
                except Exception:
                    continue
        return items

    def _parse_api_list(self, data: object, base: str) -> list[SearchResultItem]:
        rows: list = []
        if isinstance(data, dict):
            rows = data.get("data") or data.get("items") or data.get("purchases") or []
        elif isinstance(data, list):
            rows = data
        out: list[SearchResultItem] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            title = row.get("object_info") or row.get("title") or row.get("name")
            pid = row.get("purchase_number") or row.get("reg_number") or row.get("id")
            if not title:
                continue
            url = row.get("url") or row.get("link")
            if not url and pid:
                url = f"https://zakupki.gov.ru/epz/order/notice/ea20/view/common-info.html?regNumber={pid}"
            if not url:
                continue
            out.append(
                SearchResultItem(
                    title=str(title)[:500],
                    url=str(url) if str(url).startswith("http") else urljoin(base, str(url)),
                    external_id=str(pid) if pid else None,
                    customer_hint=row.get("customer_name") or row.get("customer"),
                )
            )
        return out

    async def enrich(self, item: SearchResultItem, keyword: str) -> TenderLead:
        return self._parse_detail(
            item,
            keyword,
            {
                "title": item.title,
                "customer_name": item.customer_hint,
                "contacts": [],
            },
        )
