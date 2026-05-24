from tender_agents.models import SearchResultItem
from tender_agents.scrape import parsers
from tender_agents.sources.base import SourceAdapter


class B2BCenterAdapter(SourceAdapter):
    source_id = "b2b_center"

    def build_search_url(self, keyword: str) -> str:
        return f"{self.base_url}/market/"

    async def search(self, keyword: str) -> list[SearchResultItem]:
        if getattr(self.backend, "name", None) == "httpx":
            return await parsers.b2b_center.search(
                keyword,
                search_url=self.build_search_url(keyword),
            )
        return await super().search(keyword)
