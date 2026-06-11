from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, HttpUrl, Field


class CollectFilters(BaseModel):
    """Фильтры для сбора тендеров."""
    date_from: Optional[date] = None
    date_to: Optional[date] = None


class CollectPlan(BaseModel):
    """План сбора тендеров."""
    platform_url: HttpUrl
    keywords: List[str] = Field(min_length=1)
    filters: CollectFilters
    max_per_keyword: int = 10
    max_pages: int = 5


class ListingItem(BaseModel):
    """Элемент списка выдачи (ссылка, заголовок, превью)."""
    url: HttpUrl
    title: Optional[str] = None
    preview: Optional[str] = None


class SearchContext(BaseModel):
    """Контекст текущего поиска для пагинации."""
    keyword: str
    filters: CollectFilters


class TenderRecord(BaseModel):
    """Полная запись о тендере (после парсинга карточки)."""
    platform: str
    external_id: Optional[str] = None
    title: str
    url: HttpUrl
    customer_name: Optional[str] = None
    publish_date: Optional[date] = None
    deadline: Optional[date] = None
    price: Optional[str] = None
    matched_keyword: Optional[str] = None
    contacts: Optional[str] = None
    raw_snippet: Optional[str] = None
    collected_at: datetime = Field(default_factory=datetime.now)


class CollectResult(BaseModel):
    """Результаты сбора тендеров."""
    totals_per_keyword: dict[str, int] = Field(default_factory=dict)
    errors_count: int = 0
    records: List[TenderRecord] = Field(default_factory=list)
