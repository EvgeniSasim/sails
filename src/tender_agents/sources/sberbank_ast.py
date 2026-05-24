from urllib.parse import urlencode

from tender_agents.models import SearchResultItem
from tender_agents.scrape import parsers
from tender_agents.sources.base import SourceAdapter


class SberbankAstAdapter(SourceAdapter):
    source_id = "sberbank_ast"

    def build_search_url(self, keyword: str) -> str:
        params = {"search": keyword}
        return f"{self.search_url}?{urlencode(params)}"

    async def search(self, keyword: str) -> list[SearchResultItem]:
        if getattr(self.backend, "name", None) == "httpx":
            return await parsers.sberbank_ast.search(
                keyword,
                search_url=self.build_search_url(keyword),
                base_url=self.base_url,
            )
        return await super().search(keyword)
