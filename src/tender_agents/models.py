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


class KeywordStats(BaseModel):
    """Статистика по ключевому слову."""
    found_links: int = 0
    saved: int = 0
    skipped_duplicate: int = 0
    skipped_filter: int = 0
    errors: int = 0
    duration_seconds: float = 0.0


class CollectResult(BaseModel):
    """Результаты сбора тендеров."""
    totals_per_keyword: dict[str, int] = Field(default_factory=dict)
    errors_count: int = 0
    duplicates_count: int = 0
    filtered_count: int = 0
    records: List[TenderRecord] = Field(default_factory=list)

    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    platform_host: Optional[str] = None
    keyword_stats: dict[str, KeywordStats] = Field(default_factory=dict)

    @property
    def duration_seconds(self) -> float:
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return 0.0
