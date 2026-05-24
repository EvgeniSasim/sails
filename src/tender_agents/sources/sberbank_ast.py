import logging
from urllib.parse import urlencode

from tender_agents.models import SearchResultItem
from tender_agents.scrape import parsers
from tender_agents.sources.base import SourceAdapter

logger = logging.getLogger(__name__)


class SberbankAstAdapter(SourceAdapter):
    source_id = "sberbank_ast"

    def build_search_url(self, keyword: str) -> str:
        params = {"search": keyword}
        return f"{self.search_url}?{urlencode(params)}"

    async def search(self, keyword: str) -> list[SearchResultItem]:
        """Нативный httpx-парсер; Playwright на ЕИС часто таймаутит (сайт/сеть)."""
        try:
            return await parsers.sberbank_ast.search(
                keyword,
                search_url=self.search_url,
                base_url=self.base_url,
            )
        except Exception as e:
            logger.warning("sberbank_ast: поиск «%s» пропущен (%s)", keyword, e)
            return []
