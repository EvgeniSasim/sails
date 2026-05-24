from abc import ABC, abstractmethod

from tender_agents.models import SearchResultItem, TenderLead, TenderStatus
from tender_agents.scrape.base import ExtractBackend


class SourceAdapter(ABC):
    source_id: str

    def __init__(self, config: dict, backend: ExtractBackend):
        self.config = config
        self.backend = backend
        self.base_url = config.get("base_url", "").rstrip("/")
        self.search_url = config.get("search_url", "")

    @abstractmethod
    def build_search_url(self, keyword: str) -> str:
        ...

    async def search(self, keyword: str) -> list[SearchResultItem]:
        url = self.build_search_url(keyword)
        data = await self.backend.extract_list(
            url,
            keyword=keyword,
            source_name=self.config.get("name", self.source_id),
        )
        data["_keyword"] = keyword
        return self._parse_list(data, keyword=keyword)

    async def enrich(self, item: SearchResultItem, keyword: str) -> TenderLead:
        data = await self.backend.extract_detail(item.url, keyword=keyword)
        return self._parse_detail(item, keyword, data)

    def _parse_list(self, data: dict, *, keyword: str = "") -> list[SearchResultItem]:
        from tender_agents.scrape.filters import filter_search_items

        items_raw = data.get("items") or data.get("results") or []
        if not isinstance(items_raw, list):
            return []
        out: list[SearchResultItem] = []
        for row in items_raw:
            if not isinstance(row, dict):
                continue
            title = row.get("title") or row.get("name")
            url = row.get("url") or row.get("link")
            if not title or not url:
                continue
            url = self._abs_url(str(url))
            out.append(
                SearchResultItem(
                    title=str(title).strip(),
                    url=url,
                    external_id=_str_or_none(row.get("external_id") or row.get("id")),
                    status_hint=_str_or_none(row.get("status_hint") or row.get("status")),
                    customer_hint=_str_or_none(row.get("customer_hint") or row.get("customer")),
                )
            )
        kw = keyword or data.get("_keyword") or ""
        return filter_search_items(out, keyword=kw, source_id=self.source_id)

    def _parse_detail(
        self, item: SearchResultItem, keyword: str, data: dict
    ) -> TenderLead:
        from tender_agents.models import Contact

        contacts_raw = data.get("contacts") or []
        contacts = []
        if isinstance(contacts_raw, list):
            for c in contacts_raw:
                if isinstance(c, dict):
                    contacts.append(
                        Contact(
                            name=_str_or_none(c.get("name")),
                            role=_str_or_none(c.get("role")),
                            phone=_str_or_none(c.get("phone")),
                            email=_str_or_none(c.get("email")),
                            organization=_str_or_none(c.get("organization")),
                            linkedin_search_url=_str_or_none(c.get("linkedin_search_url")),
                            yandex_search_url=_str_or_none(c.get("yandex_search_url")),
                            source_snippet=_str_or_none(c.get("source_snippet")),
                        )
                    )

        from tender_agents.text_utils import normalize_title

        status = _map_status(data.get("status") or item.status_hint)
        title = normalize_title(_str_or_none(data.get("title")) or item.title)
        return TenderLead(
            source=self.source_id,
            external_id=item.external_id or _str_or_none(data.get("external_id")),
            title=title,
            url=item.url,
            status=status,
            customer_name=_str_or_none(data.get("customer_name")) or item.customer_hint,
            customer_inn=_str_or_none(data.get("customer_inn")),
            price=_str_or_none(data.get("price")),
            publish_date=_str_or_none(data.get("publish_date")),
            end_date=_str_or_none(data.get("end_date")),
            description_snippet=_str_or_none(data.get("description_snippet")),
            matched_keyword=keyword,
            contacts=contacts,
            raw_extract=data,
        )

    def _abs_url(self, url: str) -> str:
        if url.startswith("http"):
            return url
        if url.startswith("/"):
            return f"{self.base_url}{url}"
        return f"{self.base_url}/{url}"


def _str_or_none(v: object) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _map_status(hint: object) -> TenderStatus:
    if hint is None:
        return TenderStatus.UNKNOWN
    s = str(hint).lower()
    if any(x in s for x in ("заверш", "оконч", "completed", "closed", "архив")):
        return TenderStatus.COMPLETED
    if any(x in s for x in ("актив", "приём", "active", "open", "подач")):
        return TenderStatus.ACTIVE
    return TenderStatus.UNKNOWN
