from urllib.parse import urlencode

from tender_agents.models import SearchResultItem, TenderLead
from tender_agents.scrape import parsers
from tender_agents.sources.base import SourceAdapter


class ZakupkiAdapter(SourceAdapter):
    """ЕИС — нативный бесплатный парсер (httpx), без LLM."""

    source_id = "zakupki"

    def build_search_url(self, keyword: str) -> str:
        params = {
            "searchString": keyword,
            "morphology": "on",
            "pageNumber": "1",
            "recordsPerPage": "_20",
        }
        return f"{self.search_url}?{urlencode(params, safe='+')}"

    async def search(self, keyword: str) -> list[SearchResultItem]:
        return await parsers.zakupki.search(keyword, max_pages=1)

    async def enrich(self, item: SearchResultItem, keyword: str) -> TenderLead:
        # Yandex-агент для обогащения; поиск остаётся бесплатным нативным парсером
        if getattr(self.backend, "name", None) == "yandex":
            return await super().enrich(item, keyword)
        detail_url = parsers.zakupki.normalize_detail_url(item.url)
        data = await parsers.zakupki.enrich_detail(
            detail_url,
            fallback_title=item.title,
            customer_hint=item.customer_hint,
        )
        lead = self._parse_detail(item, keyword, data)
        used = data.get("_detail_url_used")
        if used and used != item.url:
            lead.url = used
        return lead
