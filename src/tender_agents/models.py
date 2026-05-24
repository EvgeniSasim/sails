from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class TenderStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    UNKNOWN = "unknown"


class LeadSegment(StrEnum):
    HR = "hr"
    CX = "cx"
    RESEARCH = "research"
    GOV = "gov"
    OTHER = "other"


class PipelineStatus(StrEnum):
    NEW = "new"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    DEMO = "demo"
    WON = "won"
    LOST = "lost"


class Contact(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str | None = None
    role: str | None = None
    phone: str | None = None
    email: str | None = None
    organization: str | None = None
    # открытые подсказки для продаж (не персональные данные из закрытых API)
    linkedin_search_url: str | None = None
    yandex_search_url: str | None = None
    source_snippet: str | None = None


class TenderLead(BaseModel):
    """Карточка лида: тендеры ЕИС и записи из открытых каналов (СМИ, рейтинги)."""

    id: int | None = None
    source: str
    external_id: str | None = None
    title: str
    url: str
    status: TenderStatus = TenderStatus.UNKNOWN
    customer_name: str | None = None
    customer_inn: str | None = None
    price: str | None = None
    publish_date: str | None = None
    end_date: str | None = None
    description_snippet: str | None = None
    matched_keyword: str | None = None
    contacts: list[Contact] = Field(default_factory=list)
    raw_extract: dict | None = None
    # канал воронки: tender = закупки; open_media = рейтинги/статьи и т.п.
    channel: str = "tender"
    context_url: str | None = None
    context_title: str | None = None
    # продажи FeedBackTalk
    score: int = 0
    segment: LeadSegment = LeadSegment.OTHER
    pipeline_status: PipelineStatus = PipelineStatus.NEW
    score_reasons: list[str] = Field(default_factory=list)
    pitch: str | None = None
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SearchResultItem(BaseModel):
    title: str
    url: str
    external_id: str | None = None
    status_hint: str | None = None
    customer_hint: str | None = None


class SearchTask(BaseModel):
    source: str
    keyword: str
    search_url: str


class EnrichTask(BaseModel):
    lead: TenderLead


class ContactAppearance(BaseModel):
    """Упоминание / выступление / публикация, связанная с контактом."""

    model_config = ConfigDict(extra="ignore")

    id: int | None = None
    profile_id: int | None = None
    appeared_at: datetime | None = None
    source_kind: str = ""
    source_url: str = ""
    source_title: str | None = None
    snippet: str | None = None
    appearance_type: str = ""
    meta_json: dict | None = None
    created_at: datetime | None = None


class ContactProfile(BaseModel):
    """Контакт для продаж: организация, должность, ФИО, каналы связи, актуальность."""

    model_config = ConfigDict(extra="ignore")

    id: int | None = None
    organization: str
    full_name: str
    position: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    linkedin_search_url: str | None = None
    yandex_search_url: str | None = None
    telegram: str | None = None
    vk: str | None = None
    social_json: dict | None = None
    notes: str | None = None
    bio: str | None = None
    channel_verified_at: datetime | None = None
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    appearance_count: int = 0
    last_enriched_at: datetime | None = None
    # fresh ≤365д, aging ≤730д, stale старше, partial — нет явной даты
    data_quality: str = "unknown"
    appearances: list[ContactAppearance] = Field(default_factory=list)
