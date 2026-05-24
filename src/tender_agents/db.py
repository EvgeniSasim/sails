from datetime import date, datetime, timezone

from sqlalchemy import JSON, DateTime, Integer, String, Text, and_, case, delete, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Mapped, mapped_column

from tender_agents.orm import Base
from tender_agents.models import (
    Contact,
    LeadSegment,
    PipelineStatus,
    TenderLead,
    TenderStatus,
)
from tender_agents.settings import settings

MIGRATION_COLUMNS = [
    ("score", "INTEGER DEFAULT 0"),
    ("segment", "VARCHAR(32) DEFAULT 'other'"),
    ("pipeline_status", "VARCHAR(32) DEFAULT 'new'"),
    ("score_reasons_json", "JSON"),
    ("pitch", "TEXT"),
    ("notes", "TEXT"),
    ("channel", "VARCHAR(32) DEFAULT 'tender'"),
    ("context_url", "VARCHAR(1024)"),
    ("context_title", "TEXT"),
]


class LeadRow(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(64), index=True)
    external_id: Mapped[str | None] = mapped_column(String(128), index=True)
    url: Mapped[str] = mapped_column(String(1024), unique=True)
    title: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default=TenderStatus.UNKNOWN)
    customer_name: Mapped[str | None] = mapped_column(String(512))
    customer_inn: Mapped[str | None] = mapped_column(String(32), index=True)
    price: Mapped[str | None] = mapped_column(String(128))
    publish_date: Mapped[str | None] = mapped_column(String(64))
    end_date: Mapped[str | None] = mapped_column(String(64))
    description_snippet: Mapped[str | None] = mapped_column(Text)
    matched_keyword: Mapped[str | None] = mapped_column(String(256))
    contacts_json: Mapped[list | None] = mapped_column(JSON)
    raw_extract: Mapped[dict | None] = mapped_column(JSON)
    score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    segment: Mapped[str] = mapped_column(String(32), default=LeadSegment.OTHER, index=True)
    pipeline_status: Mapped[str] = mapped_column(
        String(32), default=PipelineStatus.NEW, index=True
    )
    score_reasons_json: Mapped[list | None] = mapped_column(JSON)
    pitch: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(String(32), default="tender", index=True)
    context_url: Mapped[str | None] = mapped_column(String(1024))
    context_title: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


def _lead_to_row(lead: TenderLead) -> LeadRow:
    return LeadRow(
        source=lead.source,
        external_id=lead.external_id,
        url=lead.url,
        title=lead.title,
        status=lead.status.value,
        customer_name=lead.customer_name,
        customer_inn=lead.customer_inn,
        price=lead.price,
        publish_date=lead.publish_date,
        end_date=lead.end_date,
        description_snippet=lead.description_snippet,
        matched_keyword=lead.matched_keyword,
        contacts_json=[c.model_dump(exclude_none=True) for c in lead.contacts],
        raw_extract=lead.raw_extract,
        score=lead.score,
        segment=lead.segment.value,
        pipeline_status=lead.pipeline_status.value,
        score_reasons_json=lead.score_reasons,
        pitch=lead.pitch,
        notes=lead.notes,
        channel=lead.channel,
        context_url=lead.context_url,
        context_title=lead.context_title,
    )


def _row_to_lead(row: LeadRow) -> TenderLead:
    contacts = [Contact(**c) for c in (row.contacts_json or [])]
    return TenderLead(
        id=row.id,
        source=row.source,
        external_id=row.external_id,
        title=row.title,
        url=row.url,
        status=TenderStatus(row.status),
        customer_name=row.customer_name,
        customer_inn=row.customer_inn,
        price=row.price,
        publish_date=row.publish_date,
        end_date=row.end_date,
        description_snippet=row.description_snippet,
        matched_keyword=row.matched_keyword,
        contacts=contacts,
        raw_extract=row.raw_extract,
        score=row.score or 0,
        segment=LeadSegment(row.segment or LeadSegment.OTHER),
        pipeline_status=PipelineStatus(row.pipeline_status or PipelineStatus.NEW),
        score_reasons=list(row.score_reasons_json or []),
        pitch=row.pitch,
        notes=row.notes,
        channel=getattr(row, "channel", None) or "tender",
        context_url=getattr(row, "context_url", None),
        context_title=getattr(row, "context_title", None),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class LeadFilters:
    def __init__(
        self,
        *,
        min_score: int = 0,
        segment: str | None = None,
        pipeline_status: str | None = None,
        source: str | None = None,
        has_contact: bool = False,
        active_only: bool = False,
        q: str = "",
        channel: str | None = None,
        matched_keywords: list[str] | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ):
        self.min_score = min_score
        self.segment = segment
        self.pipeline_status = pipeline_status
        self.source = source
        self.has_contact = has_contact
        self.active_only = active_only
        self.q = q
        self.channel = channel
        self.matched_keywords = [k.strip() for k in (matched_keywords or []) if k.strip()]
        self.date_from = date_from
        self.date_to = date_to


class LeadRepository:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        engine,
    ):
        self._session_factory = session_factory
        self._engine = engine
        self._contacts_repo = None
        self._research_jobs = None
        self._provenance = None

    def contacts_repo(self):
        if self._contacts_repo is None:
            import tender_agents.contacts_db as cdb

            self._contacts_repo = cdb.ContactRepository(self._session_factory, self._engine)
        return self._contacts_repo

    def research_jobs(self):
        if self._research_jobs is None:
            from tender_agents.research.jobs import ResearchJobRepository

            self._research_jobs = ResearchJobRepository(self._session_factory, self._engine)
        return self._research_jobs

    def provenance(self):
        if self._provenance is None:
            from tender_agents.compliance import ProvenanceRepository

            self._provenance = ProvenanceRepository(self._session_factory, self._engine)
        return self._provenance

    async def init(self) -> None:
        import tender_agents.compliance  # noqa: F401
        import tender_agents.contacts_db  # noqa: F401
        import tender_agents.research.jobs  # noqa: F401

        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await self._migrate(conn)
        await self.contacts_repo().migrate_appearance_columns()
        await self.contacts_repo().migrate_profile_columns()
        await self.research_jobs().ensure_tables()
        await self.provenance().ensure_tables()
        await self.contacts_repo().backfill_open_media_from_leads_if_needed()

    async def _migrate(self, conn) -> None:
        def run(sync_conn):
            for col, ddl in MIGRATION_COLUMNS:
                try:
                    sync_conn.execute(text(f"ALTER TABLE leads ADD COLUMN {col} {ddl}"))
                except Exception:
                    pass

        await conn.run_sync(run)

    async def upsert(self, lead: TenderLead) -> LeadRow:
        async with self._session_factory() as session:
            result = await session.execute(select(LeadRow).where(LeadRow.url == lead.url))
            existing = result.scalar_one_or_none()
            if existing:
                existing.title = lead.title
                existing.status = lead.status.value
                existing.customer_name = lead.customer_name
                existing.customer_inn = lead.customer_inn
                existing.price = lead.price
                existing.publish_date = lead.publish_date
                existing.end_date = lead.end_date
                existing.description_snippet = lead.description_snippet
                existing.matched_keyword = lead.matched_keyword
                existing.contacts_json = [c.model_dump(exclude_none=True) for c in lead.contacts]
                existing.raw_extract = lead.raw_extract
                existing.score = lead.score
                existing.segment = lead.segment.value
                existing.score_reasons_json = lead.score_reasons
                existing.pitch = lead.pitch
                if lead.notes is not None:
                    existing.notes = lead.notes
                existing.channel = lead.channel
                existing.context_url = lead.context_url
                existing.context_title = lead.context_title
                existing.updated_at = datetime.now(timezone.utc)
                await session.commit()
                await session.refresh(existing)
                return existing
            row = _lead_to_row(lead)
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return row

    async def get_by_id(self, lead_id: int) -> TenderLead | None:
        async with self._session_factory() as session:
            result = await session.execute(select(LeadRow).where(LeadRow.id == lead_id))
            row = result.scalar_one_or_none()
            return _row_to_lead(row) if row else None

    async def update_pipeline(
        self, lead_id: int, *, pipeline_status: str, notes: str | None = None
    ) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(select(LeadRow).where(LeadRow.id == lead_id))
            row = result.scalar_one_or_none()
            if not row:
                return False
            row.pipeline_status = pipeline_status
            if notes is not None:
                row.notes = notes
            row.updated_at = datetime.now(timezone.utc)
            await session.commit()
            return True

    def _apply_filters(self, query, flt: LeadFilters):
        if flt.min_score:
            query = query.where(LeadRow.score >= flt.min_score)
        if flt.segment:
            query = query.where(LeadRow.segment == flt.segment)
        if flt.pipeline_status:
            query = query.where(LeadRow.pipeline_status == flt.pipeline_status)
        if flt.source:
            query = query.where(LeadRow.source == flt.source)
        if flt.channel:
            query = query.where(LeadRow.channel == flt.channel)
        if flt.active_only:
            query = query.where(LeadRow.status == TenderStatus.ACTIVE)
        if flt.matched_keywords:
            kws = flt.matched_keywords
            clauses = []
            for kw in kws:
                pat = f"%{kw.lower()}%"
                clauses.append(func.lower(LeadRow.matched_keyword).like(pat))
                clauses.append(func.lower(LeadRow.title).like(pat))
            query = query.where(or_(*clauses))
        if flt.q and flt.q.strip():
            term = (
                flt.q.strip()
                .replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )
            pat = f"%{term.lower()}%"
            query = query.where(
                or_(
                    func.lower(LeadRow.title).like(pat, escape="\\"),
                    func.lower(LeadRow.customer_name).like(pat, escape="\\"),
                    func.lower(LeadRow.context_title).like(pat, escape="\\"),
                )
            )
        if flt.date_from or flt.date_to:
            query = self._apply_date_range(query, flt.date_from, flt.date_to)
        return query

    @staticmethod
    def _publish_date_iso_expr():
        return case(
            (
                and_(
                    LeadRow.publish_date.isnot(None),
                    func.length(LeadRow.publish_date) >= 10,
                    func.substr(LeadRow.publish_date, 5, 1) == "-",
                ),
                func.substr(LeadRow.publish_date, 1, 10),
            ),
            (
                and_(
                    LeadRow.publish_date.isnot(None),
                    func.length(LeadRow.publish_date) == 10,
                    func.substr(LeadRow.publish_date, 3, 1) == ".",
                ),
                func.concat(
                    func.substr(LeadRow.publish_date, 7, 4),
                    "-",
                    func.substr(LeadRow.publish_date, 4, 2),
                    "-",
                    func.substr(LeadRow.publish_date, 1, 2),
                ),
            ),
            else_=func.strftime("%Y-%m-%d", LeadRow.created_at),
        )

    def _apply_date_range(self, query, date_from: date | None, date_to: date | None):
        iso = self._publish_date_iso_expr()
        if date_from:
            query = query.where(iso >= date_from.isoformat())
        if date_to:
            query = query.where(iso <= date_to.isoformat())
        return query

    @staticmethod
    def _end_date_iso_expr():
        """Дедлайн в БД часто dd.mm.yyyy — приводим к ISO для корректной сортировки."""
        return case(
            (
                and_(
                    LeadRow.end_date.isnot(None),
                    func.length(LeadRow.end_date) == 10,
                    func.substr(LeadRow.end_date, 3, 1) == ".",
                    func.substr(LeadRow.end_date, 6, 1) == ".",
                ),
                func.concat(
                    func.substr(LeadRow.end_date, 7, 4),
                    "-",
                    func.substr(LeadRow.end_date, 4, 2),
                    "-",
                    func.substr(LeadRow.end_date, 1, 2),
                ),
            ),
            else_=None,
        )

    def _order_exprs(self, sort_by: str, order: str):
        desc = order != "asc"
        iso = self._end_date_iso_expr()
        invalid_end = case((iso.is_(None), 1), else_=0)

        if sort_by == "urgency":
            # сначала с известным дедлайном (ближе по дате), затем скор
            return (
                invalid_end.asc(),
                iso.asc().nulls_last(),
                LeadRow.score.desc(),
                LeadRow.id.desc(),
            )

        if sort_by == "end_date":
            tail = (
                LeadRow.score.desc(),
                LeadRow.id.desc(),
            )
            if desc:
                return (invalid_end.asc(), iso.desc().nulls_last(), *tail)
            return (invalid_end.asc(), iso.asc().nulls_last(), *tail)

        cols = {
            "score": LeadRow.score,
            "segment": LeadRow.segment,
            "title": LeadRow.title,
            "customer": LeadRow.customer_name,
            "pipeline": LeadRow.pipeline_status,
            "updated": LeadRow.updated_at,
            "source": LeadRow.source,
            "channel": LeadRow.channel,
        }
        col = cols.get(sort_by, LeadRow.score)
        primary = col.desc() if desc else col.asc()
        if sort_by == "score":
            return (primary, LeadRow.updated_at.desc(), LeadRow.id.desc())
        return (primary, LeadRow.score.desc(), LeadRow.id.desc())

    async def list_filtered(
        self,
        flt: LeadFilters | None = None,
        *,
        limit: int = 200,
        offset: int = 0,
        sort_by: str = "score",
        order: str = "desc",
    ) -> list[TenderLead]:
        flt = flt or LeadFilters()
        async with self._session_factory() as session:
            query = select(LeadRow).order_by(*self._order_exprs(sort_by, order))
            query = self._apply_filters(query, flt)
            result = await session.execute(query.offset(offset).limit(limit))
            leads = [_row_to_lead(r) for r in result.scalars().all()]
        if flt.has_contact:
            leads = [l for l in leads if any(c.email or c.phone for c in l.contacts)]
        return leads

    async def list_all(self, limit: int = 100) -> list[TenderLead]:
        return await self.list_filtered(LeadFilters(), limit=limit)

    async def count_by_pipeline(self, *, channel: str | None = None) -> dict[str, int]:
        async with self._session_factory() as session:
            q = select(LeadRow)
            if channel:
                q = q.where(LeadRow.channel == channel)
            result = await session.execute(q)
            rows = result.scalars().all()
        counts: dict[str, int] = {}
        for r in rows:
            counts[r.pipeline_status] = counts.get(r.pipeline_status, 0) + 1
        return counts

    async def count_by_segment(self, *, channel: str | None = None) -> dict[str, int]:
        async with self._session_factory() as session:
            q = select(LeadRow)
            if channel:
                q = q.where(LeadRow.channel == channel)
            result = await session.execute(q)
            rows = result.scalars().all()
        counts: dict[str, int] = {}
        for r in rows:
            counts[r.segment] = counts.get(r.segment, 0) + 1
        return counts

    async def stats(self, *, channel: str | None = None) -> dict:
        async with self._session_factory() as session:
            result = await session.execute(select(LeadRow))
            rows = list(result.scalars().all())
        if channel:
            rows = [r for r in rows if (getattr(r, "channel", None) or "tender") == channel]
        if not rows:
            return {
                "total": 0,
                "avg_score": 0,
                "with_contact": 0,
                "with_search_hints": 0,
                "hot": 0,
                "by_channel": {},
            }
        with_contact = sum(
            1 for r in rows if r.contacts_json and any(c.get("email") or c.get("phone") for c in r.contacts_json)
        )
        with_hints = sum(
            1
            for r in rows
            if r.contacts_json
            and any(
                c.get("linkedin_search_url") or c.get("yandex_search_url")
                for c in r.contacts_json
            )
        )
        hot = sum(1 for r in rows if (r.score or 0) >= 60)
        avg = sum(r.score or 0 for r in rows) / len(rows)
        by_channel: dict[str, int] = {}
        for r in rows:
            ch = getattr(r, "channel", None) or "tender"
            by_channel[ch] = by_channel.get(ch, 0) + 1
        return {
            "total": len(rows),
            "avg_score": round(avg, 1),
            "with_contact": with_contact,
            "with_search_hints": with_hints,
            "hot": hot,
            "by_channel": by_channel,
        }

    async def delete_by_urls(self, urls: list[str]) -> int:
        if not urls:
            return 0
        async with self._session_factory() as session:
            result = await session.execute(delete(LeadRow).where(LeadRow.url.in_(urls)))
            await session.commit()
            return result.rowcount or 0

    async def delete_low_score(self, min_score: int = 40) -> int:
        async with self._session_factory() as session:
            result = await session.execute(delete(LeadRow).where(LeadRow.score < min_score))
            await session.commit()
            return result.rowcount or 0


def create_repository() -> LeadRepository:
    url = settings.database_url
    if url.startswith("sqlite"):
        from pathlib import Path

        path_part = url.split("///", 1)[-1] if "///" in url else ""
        if path_part and not path_part.startswith(":"):
            Path(path_part).parent.mkdir(parents=True, exist_ok=True)
    engine = create_async_engine(url, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    return LeadRepository(factory, engine)
