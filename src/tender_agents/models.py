from datetime import date
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
