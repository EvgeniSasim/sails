"""Отдельная база контактов (СМИ / рейтинги): организация, ФИО, должность, появления, каналы связи."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, delete, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column

from tender_agents.models import Contact, ContactAppearance, ContactProfile, TenderLead
from tender_agents.orm import Base

logger = logging.getLogger(__name__)

META_KEY_OPEN_MEDIA_MIGRATED = "open_media_migrated_v1"


class SchemaMetaRow(Base):
    __tablename__ = "_schema_meta"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(256))


class ContactProfileRow(Base):
    __tablename__ = "contact_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dedup_key: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    organization: Mapped[str] = mapped_column(String(512), index=True)
    full_name: Mapped[str] = mapped_column(String(256), index=True)
    position: Mapped[str | None] = mapped_column(String(512))
    email: Mapped[str | None] = mapped_column(String(256))
    phone: Mapped[str | None] = mapped_column(String(128))
    linkedin_url: Mapped[str | None] = mapped_column(Text)
    linkedin_search_url: Mapped[str | None] = mapped_column(Text)
    yandex_search_url: Mapped[str | None] = mapped_column(Text)
    telegram: Mapped[str | None] = mapped_column(String(128))
    vk: Mapped[str | None] = mapped_column(String(256))
    social_json: Mapped[dict | None] = mapped_column(JSON)
    notes: Mapped[str | None] = mapped_column(Text)
    bio: Mapped[str | None] = mapped_column(Text)
    channel_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    appearance_count: Mapped[int] = mapped_column(Integer, default=0)
    last_enriched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ContactAppearanceRow(Base):
    __tablename__ = "contact_appearances"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("contact_profiles.id", ondelete="CASCADE"), index=True
    )
    appeared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    source_kind: Mapped[str] = mapped_column(String(64), default="")
    source_url: Mapped[str] = mapped_column(Text)
    source_title: Mapped[str | None] = mapped_column(Text)
    snippet: Mapped[str | None] = mapped_column(Text)
    appearance_type: Mapped[str | None] = mapped_column(String(32), default="")
    meta_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


APPEARANCE_MIGRATION_COLUMNS = [
    ("appearance_type", "VARCHAR(32) DEFAULT ''"),
    ("meta_json", "TEXT"),
]

PROFILE_MIGRATION_COLUMNS = [
    ("bio", "TEXT"),
    ("channel_verified_at", "DATETIME"),
]


class TenderContactLinkRow(Base):
    """Связь тендер (leads) ↔ контакт из базы СМИ/рейтингов."""

    __tablename__ = "tender_contact_links"
    __table_args__ = (UniqueConstraint("lead_id", "contact_profile_id", name="uq_tcl_lead_contact"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    contact_profile_id: Mapped[int] = mapped_column(
        ForeignKey("contact_profiles.id", ondelete="CASCADE"), index=True
    )
    confidence: Mapped[int] = mapped_column(Integer, default=0)
    method: Mapped[str] = mapped_column(String(32), default="")
    evidence_json: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16), default="suggested", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


def _dedup_key(organization: str, full_name: str) -> str:
    o = " ".join((organization or "").lower().split())
    n = " ".join((full_name or "").lower().split())
    return f"{o}|{n}"[:512]


def _parse_pub_date(s: str | None) -> datetime | None:
    if not s or not str(s).strip():
        return None
    s = str(s).strip()[:32]
    try:
        if len(s) >= 10 and s[4] == "-":
            d = datetime.fromisoformat(s[:10].replace("Z", ""))
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            return d
        if len(s) >= 10 and s[2] == "." and s[5] == ".":
            d, m, y = s[:10].split(".")
            return datetime(int(y), int(m), int(d), tzinfo=timezone.utc)
    except (ValueError, TypeError):
        pass
    return None


def _as_utc(dt: datetime | None) -> datetime | None:
    """SQLite часто отдаёт naive datetime — приводим к UTC для сравнений."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _quality(last_seen: datetime | None) -> str:
    if not last_seen:
        return "partial"
    now = datetime.now(timezone.utc)
    last_seen = _as_utc(last_seen)
    if last_seen is None:
        return "partial"
    age = now - last_seen
    if age.days <= 365:
        return "fresh"
    if age.days <= 730:
        return "aging"
    return "stale"


def _row_to_appearance(row: ContactAppearanceRow) -> ContactAppearance:
    return ContactAppearance(
        id=row.id,
        profile_id=row.profile_id,
        appeared_at=row.appeared_at,
        source_kind=row.source_kind or "",
        source_url=row.source_url or "",
        source_title=row.source_title,
        snippet=row.snippet,
        appearance_type=row.appearance_type or "",
        meta_json=row.meta_json,
        created_at=row.created_at,
    )


@dataclass
class ResearchFindingInput:
    source_url: str
    source_title: str | None
    snippet: str | None
    source_kind: str
    appeared_at: datetime | None = None
    appearance_type: str = ""
    meta_json: dict | None = None


def _row_to_profile(row: ContactProfileRow, *, appearances: list[ContactAppearance] | None = None) -> ContactProfile:
    return ContactProfile(
        id=row.id,
        organization=row.organization,
        full_name=row.full_name,
        position=row.position,
        email=row.email,
        phone=row.phone,
        linkedin_url=row.linkedin_url,
        linkedin_search_url=row.linkedin_search_url,
        yandex_search_url=row.yandex_search_url,
        telegram=row.telegram,
        vk=row.vk,
        social_json=row.social_json,
        notes=row.notes,
        bio=getattr(row, "bio", None),
        channel_verified_at=getattr(row, "channel_verified_at", None),
        first_seen_at=row.first_seen_at,
        last_seen_at=row.last_seen_at,
        appearance_count=row.appearance_count or 0,
        last_enriched_at=row.last_enriched_at,
        data_quality=_quality(row.last_seen_at),
        appearances=appearances or [],
    )


@dataclass
class ContactListFilters:
    q: str = ""
    organization: str = ""
    has_email: bool = False
    has_phone: bool = False
    has_linkedin_hint: bool = False
    within_years: int = 0  # 0 = без отсечки по дате (удобно после импорта)


class ContactRepository:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        engine,
    ):
        self._session_factory = session_factory
        self._engine = engine

    async def migrate_appearance_columns(self) -> None:
        async with self._engine.begin() as conn:
            def run(sync_conn):
                for col, ddl in APPEARANCE_MIGRATION_COLUMNS:
                    try:
                        sync_conn.execute(
                            text(f"ALTER TABLE contact_appearances ADD COLUMN {col} {ddl}")
                        )
                    except Exception:
                        pass

            await conn.run_sync(run)

    async def migrate_profile_columns(self) -> None:
        async with self._engine.begin() as conn:
            def run(sync_conn):
                for col, ddl in PROFILE_MIGRATION_COLUMNS:
                    try:
                        sync_conn.execute(
                            text(f"ALTER TABLE contact_profiles ADD COLUMN {col} {ddl}")
                        )
                    except Exception:
                        pass

            await conn.run_sync(run)

    def _apply_list_filters(self, query, flt: ContactListFilters):
        if flt.within_years and flt.within_years > 0:
            cutoff = datetime.now(timezone.utc) - timedelta(days=365 * flt.within_years)
            query = query.where(ContactProfileRow.last_seen_at >= cutoff)
        if flt.organization.strip():
            pat = f"%{flt.organization.strip().lower()}%"
            query = query.where(func.lower(ContactProfileRow.organization).like(pat))
        if flt.q.strip():
            term = (
                flt.q.strip()
                .replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )
            pat = f"%{term.lower()}%"
            query = query.where(
                or_(
                    func.lower(ContactProfileRow.full_name).like(pat, escape="\\"),
                    func.lower(ContactProfileRow.organization).like(pat, escape="\\"),
                    func.lower(ContactProfileRow.position).like(pat, escape="\\"),
                )
            )
        if flt.has_email:
            query = query.where(
                ContactProfileRow.email.isnot(None), func.length(func.trim(ContactProfileRow.email)) > 0
            )
        if flt.has_phone:
            query = query.where(
                ContactProfileRow.phone.isnot(None), func.length(func.trim(ContactProfileRow.phone)) > 0
            )
        if flt.has_linkedin_hint:
            query = query.where(
                or_(
                    ContactProfileRow.linkedin_search_url.isnot(None),
                    ContactProfileRow.linkedin_url.isnot(None),
                )
            )
        return query

    def _order_exprs(self, sort_by: str, order: str):
        desc = order != "asc"
        cols = {
            "last_seen": ContactProfileRow.last_seen_at,
            "organization": ContactProfileRow.organization,
            "full_name": ContactProfileRow.full_name,
            "appearances": ContactProfileRow.appearance_count,
            "position": ContactProfileRow.position,
        }
        col = cols.get(sort_by, ContactProfileRow.last_seen_at)
        primary = col.desc() if desc else col.asc()
        return (primary, ContactProfileRow.id.desc())

    async def count_list(self, flt: ContactListFilters) -> int:
        async with self._session_factory() as session:
            base = self._apply_list_filters(select(ContactProfileRow), flt)
            q = select(func.count()).select_from(base.subquery())
            r = await session.execute(q)
            return int(r.scalar() or 0)

    async def stats_summary(self, *, within_years: int = 2) -> dict[str, Any]:
        flt = ContactListFilters(within_years=within_years)
        async with self._session_factory() as session:
            base = self._apply_list_filters(select(ContactProfileRow), flt)
            sub = base.subquery()
            total = int((await session.execute(select(func.count()).select_from(sub))).scalar() or 0)
            with_email = int(
                (
                    await session.execute(
                        select(func.count()).select_from(
                            self._apply_list_filters(select(ContactProfileRow), flt)
                            .where(
                                ContactProfileRow.email.isnot(None),
                                ContactProfileRow.email != "",
                            )
                            .subquery()
                        )
                    )
                ).scalar()
                or 0
            )
            with_phone = int(
                (
                    await session.execute(
                        select(func.count()).select_from(
                            self._apply_list_filters(select(ContactProfileRow), flt)
                            .where(
                                ContactProfileRow.phone.isnot(None),
                                ContactProfileRow.phone != "",
                            )
                            .subquery()
                        )
                    )
                ).scalar()
                or 0
            )
            apps = int(
                (
                    await session.execute(
                        select(func.coalesce(func.sum(sub.c.appearance_count), 0)).select_from(sub)
                    )
                ).scalar()
                or 0
            )
        return {
            "total": total,
            "with_email": with_email,
            "with_phone": with_phone,
            "appearance_sum": apps,
        }

    async def list_profiles(
        self,
        flt: ContactListFilters,
        *,
        sort_by: str = "last_seen",
        order: str = "desc",
        limit: int = 200,
        offset: int = 0,
    ) -> list[ContactProfile]:
        async with self._session_factory() as session:
            q = select(ContactProfileRow)
            q = self._apply_list_filters(q, flt)
            q = q.order_by(*self._order_exprs(sort_by, order))
            q = q.offset(offset).limit(limit)
            result = await session.execute(q)
            rows = list(result.scalars().all())
        return [_row_to_profile(r) for r in rows]

    async def get_by_id(self, profile_id: int, *, with_appearances: bool = True) -> ContactProfile | None:
        async with self._session_factory() as session:
            r = await session.execute(select(ContactProfileRow).where(ContactProfileRow.id == profile_id))
            row = r.scalar_one_or_none()
            if not row:
                return None
            apps: list[ContactAppearance] = []
            if with_appearances:
                ar = await session.execute(
                    select(ContactAppearanceRow)
                    .where(ContactAppearanceRow.profile_id == profile_id)
                    .order_by(
                        ContactAppearanceRow.appeared_at.desc().nulls_last(),
                        ContactAppearanceRow.id.desc(),
                    )
                )
                apps = [_row_to_appearance(x) for x in ar.scalars().all()]
            return _row_to_profile(row, appearances=apps)

    async def upsert_open_media_batch(self, leads: list[TenderLead]) -> int:
        """Сохранить / обновить контакты из лидов open_media (без таблицы leads)."""
        n = 0
        now = datetime.now(timezone.utc)
        async with self._session_factory() as session:
            for lead in leads:
                if lead.channel != "open_media":
                    continue
                c = lead.contacts[0] if lead.contacts else Contact()
                org = (lead.customer_name or c.organization or "").strip()
                name = (c.name or "").strip()
                if not org or not name:
                    logger.warning("open_media lead без организации или ФИО: %s", lead.url[:80])
                    continue
                dk = _dedup_key(org, name)
                appeared = _as_utc(_parse_pub_date(lead.publish_date)) or now
                src_url = (lead.context_url or lead.url or "").strip()
                src_title = (lead.context_title or lead.title or "").strip()
                snippet = (c.source_snippet or lead.description_snippet or "")[:800]

                raw = lead.raw_extract if isinstance(lead.raw_extract, dict) else {}
                bio_new = (raw.get("bio") or lead.description_snippet or "").strip()
                source_kind = str(raw.get("channel_kind") or "open_media")[:64]

                r = await session.execute(select(ContactProfileRow).where(ContactProfileRow.dedup_key == dk))
                prof = r.scalar_one_or_none()
                if prof:
                    if (c.email or "").strip():
                        prof.email = (c.email or "").strip()
                    if (c.phone or "").strip():
                        prof.phone = (c.phone or "").strip()
                    new_role = (c.role or "").strip()
                    if new_role:
                        old_role = (prof.position or "").strip()
                        if not old_role or len(new_role) > len(old_role):
                            prof.position = new_role[:512]
                    if (c.linkedin_search_url or "").strip():
                        prof.linkedin_search_url = (c.linkedin_search_url or "").strip()
                    if (c.yandex_search_url or "").strip():
                        prof.yandex_search_url = (c.yandex_search_url or "").strip()
                    if bio_new:
                        prev_bio = (prof.bio or "").strip()
                        if not prev_bio:
                            prof.bio = bio_new[:8000]
                        elif bio_new not in prev_bio:
                            prof.bio = (prev_bio + "\n\n---\n" + bio_new)[:8000]
                    note_line = snippet[:500] if snippet else ""
                    if note_line:
                        prev_notes = (prof.notes or "").strip()
                        if note_line not in prev_notes:
                            prof.notes = (
                                (prev_notes + "\n" + note_line).strip() if prev_notes else note_line
                            )[:4000]
                    fs = _as_utc(prof.first_seen_at)
                    prof.first_seen_at = min(fs, appeared) if fs else appeared
                else:
                    prof = ContactProfileRow(
                        dedup_key=dk,
                        organization=org,
                        full_name=name,
                        position=(c.role or "").strip() or None,
                        email=(c.email or "").strip() or None,
                        phone=(c.phone or "").strip() or None,
                        linkedin_url=None,
                        linkedin_search_url=(c.linkedin_search_url or "").strip() or None,
                        yandex_search_url=(c.yandex_search_url or "").strip() or None,
                        telegram=None,
                        vk=None,
                        social_json=None,
                        notes=(snippet[:4000] if snippet else None),
                        bio=bio_new[:8000] if bio_new else None,
                        first_seen_at=appeared,
                        last_seen_at=appeared,
                        appearance_count=0,
                    )
                    session.add(prof)
                    await session.flush()

                dup = await session.execute(
                    select(ContactAppearanceRow).where(
                        ContactAppearanceRow.profile_id == prof.id,
                        ContactAppearanceRow.source_url == src_url,
                    )
                )
                if dup.scalar_one_or_none() is None:
                    session.add(
                        ContactAppearanceRow(
                            profile_id=prof.id,
                            appeared_at=appeared,
                            source_kind=source_kind,
                            source_url=src_url,
                            source_title=src_title or None,
                            snippet=snippet or None,
                            appearance_type="rating",
                        )
                    )
                    prof.appearance_count = (prof.appearance_count or 0) + 1
                times = [t for t in (_as_utc(prof.last_seen_at), appeared) if t is not None]
                prof.last_seen_at = max(times) if times else now
                n += 1
            await session.commit()
        return n

    @staticmethod
    def _score_org_match(customer: str, org: str) -> tuple[int, str]:
        from tender_agents.text_utils import normalize_org_name, org_token_jaccard

        a = normalize_org_name(customer)
        b = normalize_org_name(org)
        if not a or not b:
            return 0, ""
        if a == b:
            return 94, "org_exact"
        if a in b or b in a:
            return 86, "org_substring"
        j = org_token_jaccard(customer, org)
        if j >= 0.55:
            return 74, "org_tokens"
        if j >= 0.3:
            return 54, "org_tokens_loose"
        return 0, ""

    async def count_links_by_status(self) -> dict[str, int]:
        async with self._session_factory() as session:
            r = await session.execute(
                select(TenderContactLinkRow.status, func.count())
                .select_from(TenderContactLinkRow)
                .group_by(TenderContactLinkRow.status)
            )
            rows = list(r.all())
        return {str(st or ""): int(n) for st, n in rows}

    async def rebuild_suggested_tender_contact_links(
        self, *, max_tenders: int = 350, max_contacts: int = 2500
    ) -> int:
        """Удаляет старые suggested и строит заново по совпадению организации заказчика с компанией контакта."""
        from tender_agents.db import LeadRow

        async with self._session_factory() as session:
            await session.execute(delete(TenderContactLinkRow).where(TenderContactLinkRow.status == "suggested"))
            await session.commit()

        async with self._session_factory() as session:
            tr = await session.execute(
                select(LeadRow)
                .where(LeadRow.channel == "tender")
                .where(LeadRow.customer_name.isnot(None))
                .where(func.length(func.trim(LeadRow.customer_name)) > 3)
                .limit(max_tenders)
            )
            tenders = list(tr.scalars().all())
            cr = await session.execute(select(ContactProfileRow).limit(max_contacts))
            contacts = list(cr.scalars().all())
            added = 0
            for t in tenders:
                cn = (t.customer_name or "").strip()
                if not cn:
                    continue
                for cp in contacts:
                    org = (cp.organization or "").strip()
                    if not org:
                        continue
                    score, method = self._score_org_match(cn, org)
                    if score < 58:
                        continue
                    session.add(
                        TenderContactLinkRow(
                            lead_id=t.id,
                            contact_profile_id=cp.id,
                            confidence=score,
                            method=method,
                            evidence_json={"customer": cn[:200], "organization": org[:200]},
                            status="suggested",
                        )
                    )
                    added += 1
            await session.commit()
        return added

    async def list_tender_contact_links_for_lead(self, lead_id: int) -> list[dict[str, Any]]:
        async with self._session_factory() as session:
            r = await session.execute(
                select(TenderContactLinkRow, ContactProfileRow)
                .join(ContactProfileRow, ContactProfileRow.id == TenderContactLinkRow.contact_profile_id)
                .where(TenderContactLinkRow.lead_id == lead_id)
                .where(TenderContactLinkRow.status != "rejected")
                .order_by(TenderContactLinkRow.confidence.desc(), TenderContactLinkRow.id.desc())
            )
            out: list[dict[str, Any]] = []
            for link, cp in r.all():
                out.append(
                    {
                        "link_id": link.id,
                        "contact_id": cp.id,
                        "full_name": cp.full_name,
                        "organization": cp.organization,
                        "confidence": link.confidence,
                        "method": link.method,
                        "status": link.status,
                    }
                )
            return out

    async def list_tender_contact_links_for_contact(self, contact_id: int) -> list[dict[str, Any]]:
        from tender_agents.db import LeadRow

        async with self._session_factory() as session:
            r = await session.execute(
                select(TenderContactLinkRow, LeadRow)
                .join(LeadRow, LeadRow.id == TenderContactLinkRow.lead_id)
                .where(TenderContactLinkRow.contact_profile_id == contact_id)
                .where(TenderContactLinkRow.status != "rejected")
                .order_by(TenderContactLinkRow.confidence.desc(), TenderContactLinkRow.id.desc())
            )
            out = []
            for link, lead in r.all():
                out.append(
                    {
                        "link_id": link.id,
                        "lead_id": lead.id,
                        "title": lead.title,
                        "customer_name": lead.customer_name or "",
                        "url": lead.url,
                        "confidence": link.confidence,
                        "method": link.method,
                        "status": link.status,
                    }
                )
            return out

    async def set_tender_contact_link_status(self, link_id: int, status: str) -> bool:
        if status not in ("suggested", "confirmed", "rejected"):
            return False
        async with self._session_factory() as session:
            row = await session.get(TenderContactLinkRow, link_id)
            if not row:
                return False
            row.status = status
            await session.commit()
            return True

    async def apply_research_findings(
        self, profile_id: int, findings: list[ResearchFindingInput]
    ) -> dict[str, Any]:
        """Записать находки агента: упоминания + каналы, найденные на страницах."""
        from tender_agents.text_utils import is_plausible_contact_email, is_plausible_contact_phone

        now = datetime.now(timezone.utc)
        added = 0
        skipped = 0
        channels: list[str] = []
        async with self._session_factory() as session:
            row = await session.get(ContactProfileRow, profile_id)
            if not row:
                return {"added": 0, "skipped": 0, "channels": []}
            from tender_agents.text_utils import is_usable_research_url

            for f in findings:
                url = (f.source_url or "").strip()
                if not url or not is_usable_research_url(url):
                    skipped += 1
                    continue
                dup = await session.execute(
                    select(ContactAppearanceRow).where(
                        ContactAppearanceRow.profile_id == profile_id,
                        ContactAppearanceRow.source_url == url,
                    )
                )
                if dup.scalar_one_or_none() is not None:
                    skipped += 1
                    continue
                session.add(
                    ContactAppearanceRow(
                        profile_id=profile_id,
                        appeared_at=f.appeared_at,
                        source_kind=f.source_kind or "web_mention",
                        source_url=url,
                        source_title=(f.source_title or "")[:500] or None,
                        snippet=(f.snippet or "")[:2000] or None,
                        appearance_type=(f.appearance_type or "")[:32] or None,
                        meta_json=f.meta_json,
                    )
                )
                row.appearance_count = (row.appearance_count or 0) + 1
                if f.appeared_at:
                    times = [t for t in (_as_utc(row.last_seen_at), _as_utc(f.appeared_at)) if t]
                    row.last_seen_at = max(times) if times else now
                added += 1
                meta = f.meta_json or {}
                for em in meta.get("emails") or []:
                    if is_plausible_contact_email(em) and not row.email:
                        row.email = em.strip()[:256]
                        channels.append("email")
                for ph in meta.get("phones") or []:
                    if is_plausible_contact_phone(ph) and not row.phone:
                        row.phone = ph.strip()[:128]
                        channels.append("phone")
                li = meta.get("linkedin_url")
                if li and not row.linkedin_url and "linkedin.com/in" in li.lower():
                    row.linkedin_url = li.strip()[:2048]
                    channels.append("linkedin")
                tg = meta.get("telegram")
                if tg and not row.telegram:
                    row.telegram = tg.strip()[:128]
                    channels.append("telegram")
                vk = meta.get("vk")
                if vk and not row.vk:
                    row.vk = vk.strip()[:256]
                    channels.append("vk")
            row.last_enriched_at = now
            await session.commit()
        return {"added": added, "skipped": skipped, "channels": sorted(set(channels))}

    async def sanitize_contact_channels(self, profile_id: int) -> list[str]:
        """Убрать мусор: служебные e-mail/тел., битые LinkedIn, находки unavailable."""
        from tender_agents.text_utils import (
            is_plausible_contact_email,
            is_plausible_contact_phone,
            is_usable_research_url,
        )

        cleared: list[str] = []
        async with self._session_factory() as session:
            row = await session.get(ContactProfileRow, profile_id)
            if not row:
                return cleared
            if row.email and not is_plausible_contact_email(row.email):
                row.email = None
                cleared.append("email")
            if row.phone and not is_plausible_contact_phone(row.phone):
                row.phone = None
                cleared.append("phone")
            if row.linkedin_url and not is_usable_research_url(row.linkedin_url):
                row.linkedin_url = None
                cleared.append("linkedin_url")
            junk = await session.execute(
                select(ContactAppearanceRow).where(
                    ContactAppearanceRow.profile_id == profile_id,
                )
            )
            removed = 0
            for app_row in junk.scalars().all():
                if not is_usable_research_url(app_row.source_url or ""):
                    await session.delete(app_row)
                    removed += 1
            if removed:
                row.appearance_count = max(0, (row.appearance_count or 0) - removed)
                cleared.append(f"appearances:{removed}")
            if cleared:
                await session.commit()
        return cleared

    async def apply_contact_enrichment(
        self,
        profile_id: int,
        *,
        linkedin_url: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        vk: str | None = None,
        telegram: str | None = None,
        notes_append: str | None = None,
    ) -> bool:
        from tender_agents.text_utils import is_plausible_contact_email, is_plausible_contact_phone

        now = datetime.now(timezone.utc)
        async with self._session_factory() as session:
            row = await session.get(ContactProfileRow, profile_id)
            if not row:
                return False
            if linkedin_url and (not row.linkedin_url or "linkedin.com" in linkedin_url.lower()):
                row.linkedin_url = linkedin_url.strip()[:2048]
            if email and is_plausible_contact_email(email) and not row.email:
                row.email = email.strip()[:256]
            if phone and is_plausible_contact_phone(phone) and not row.phone:
                row.phone = phone.strip()[:128]
            if vk and not row.vk:
                row.vk = vk.strip()[:256]
            if telegram and not row.telegram:
                row.telegram = telegram.strip()[:128]
            if notes_append:
                prev = (row.notes or "").strip()
                row.notes = (prev + "\n" + notes_append.strip()).strip()[:4000]
            row.last_enriched_at = now
            await session.commit()
            return True

    async def upsert_profile(self, profile: ContactProfile) -> tuple[int, bool]:
        """Вставка или слияние по dedup_key. Возвращает (id, is_new)."""
        now = datetime.now(timezone.utc)
        org = (profile.organization or "").strip() or "—"
        name = (profile.full_name or "").strip()
        if not name:
            raise ValueError("full_name required")
        dk = _dedup_key(org, name)
        async with self._session_factory() as session:
            r = await session.execute(select(ContactProfileRow).where(ContactProfileRow.dedup_key == dk))
            row = r.scalar_one_or_none()
            is_new = row is None
            if row:
                if profile.position and not row.position:
                    row.position = profile.position[:512]
                if profile.email and not row.email:
                    row.email = profile.email[:256]
                if profile.phone and not row.phone:
                    row.phone = profile.phone[:128]
                if profile.notes:
                    prev = (row.notes or "").strip()
                    row.notes = (prev + "\n" + profile.notes.strip()).strip()[:4000] if prev else profile.notes[:4000]
                row.last_seen_at = now
            else:
                row = ContactProfileRow(
                    dedup_key=dk,
                    organization=org[:512],
                    full_name=name[:256],
                    position=(profile.position or "")[:512] or None,
                    email=(profile.email or "")[:256] or None,
                    phone=(profile.phone or "")[:128] or None,
                    linkedin_url=profile.linkedin_url,
                    linkedin_search_url=profile.linkedin_search_url,
                    yandex_search_url=profile.yandex_search_url,
                    telegram=profile.telegram,
                    vk=profile.vk,
                    social_json=profile.social_json,
                    notes=(profile.notes or "")[:4000] or None,
                    first_seen_at=now,
                    last_seen_at=now,
                    appearance_count=0,
                )
                session.add(row)
                await session.flush()
            await session.commit()
            await session.refresh(row)
            return int(row.id), is_new

    async def upsert_contacts_batch(
        self, profiles: list[ContactProfile], appearances: list[ContactAppearance]
    ) -> int:
        """Вставить / обновить контакты и их упоминания из импорта Excel."""
        n = 0
        now = datetime.now(timezone.utc)
        apps_by_idx: dict[int, list[ContactAppearance]] = {}
        for app in appearances:
            idx = app.profile_id if app.profile_id is not None else -1
            apps_by_idx.setdefault(idx, []).append(app)

        async with self._session_factory() as session:
            for i, cp in enumerate(profiles):
                dk = _dedup_key(cp.organization, cp.full_name)
                r = await session.execute(
                    select(ContactProfileRow).where(ContactProfileRow.dedup_key == dk)
                )
                prof = r.scalar_one_or_none()
                if prof:
                    if cp.email:
                        prof.email = cp.email
                    if cp.phone:
                        prof.phone = cp.phone
                    if cp.position:
                        prof.position = cp.position
                    if cp.notes:
                        prev = (prof.notes or "").strip()
                        if cp.notes not in prev:
                            prof.notes = (prev + "\n" + cp.notes).strip()[:4000]
                    fs = _as_utc(prof.first_seen_at)
                    if cp.first_seen_at:
                        prof.first_seen_at = (
                            min(fs, _as_utc(cp.first_seen_at)) if fs else cp.first_seen_at
                        )
                    ls = _as_utc(prof.last_seen_at)
                    if cp.last_seen_at:
                        prof.last_seen_at = max(ls, _as_utc(cp.last_seen_at)) if ls else cp.last_seen_at
                else:
                    prof = ContactProfileRow(
                        dedup_key=dk,
                        organization=cp.organization,
                        full_name=cp.full_name,
                        position=cp.position,
                        email=cp.email,
                        phone=cp.phone,
                        notes=cp.notes,
                        first_seen_at=cp.first_seen_at or now,
                        last_seen_at=cp.last_seen_at or now,
                        appearance_count=0,
                    )
                    session.add(prof)
                    await session.flush()

                for app_data in apps_by_idx.get(i, []):
                    src_url = app_data.source_url
                    dup = await session.execute(
                        select(ContactAppearanceRow).where(
                            ContactAppearanceRow.profile_id == prof.id,
                            ContactAppearanceRow.source_url == src_url,
                            ContactAppearanceRow.source_title == app_data.source_title,
                        )
                    )
                    if dup.scalar_one_or_none() is None:
                        session.add(
                            ContactAppearanceRow(
                                profile_id=prof.id,
                                appeared_at=app_data.appeared_at or prof.last_seen_at,
                                source_kind=app_data.source_kind or "import_excel",
                                source_url=src_url,
                                source_title=app_data.source_title,
                                appearance_type=app_data.appearance_type or "event",
                                snippet=app_data.snippet,
                                meta_json=app_data.meta_json,
                            )
                        )
                        prof.appearance_count = (prof.appearance_count or 0) + 1
                n += 1
            await session.commit()
        return n

    async def update_bio(self, profile_id: int, bio: str) -> bool:
        async with self._session_factory() as session:
            row = await session.get(ContactProfileRow, profile_id)
            if not row:
                return False
            row.bio = (bio or "").strip()[:8000] or None
            await session.commit()
            return True

    async def verify_channel(self, profile_id: int) -> bool:
        async with self._session_factory() as session:
            row = await session.get(ContactProfileRow, profile_id)
            if not row:
                return False
            row.channel_verified_at = datetime.now(timezone.utc)
            await session.commit()
            return True

    async def add_manual_appearance(
        self,
        profile_id: int,
        *,
        appearance_type: str,
        source_title: str,
        source_url: str = "",
        appeared_at: datetime | None = None,
        snippet: str | None = None,
    ) -> bool:
        now = datetime.now(timezone.utc)
        async with self._session_factory() as session:
            row = await session.get(ContactProfileRow, profile_id)
            if not row:
                return False
            session.add(
                ContactAppearanceRow(
                    profile_id=profile_id,
                    appeared_at=appeared_at or now,
                    source_kind="manual",
                    source_url=(source_url or "").strip()[:2000] or f"manual://{profile_id}",
                    source_title=(source_title or "")[:500],
                    snippet=(snippet or "")[:2000] or None,
                    appearance_type=(appearance_type or "event")[:32],
                    meta_json={"from": "manager"},
                )
            )
            row.appearance_count = (row.appearance_count or 0) + 1
            row.last_seen_at = max(_as_utc(row.last_seen_at) or now, appeared_at or now)
            await session.commit()
            return True

    async def list_profiles_needing_enrichment(self, limit: int = 25) -> list[ContactProfile]:
        async with self._session_factory() as session:
            r = await session.execute(
                select(ContactProfileRow)
                .where(
                    or_(
                        ContactProfileRow.linkedin_url.is_(None),
                        ContactProfileRow.linkedin_url == "",
                    )
                )
                .order_by(ContactProfileRow.last_enriched_at.asc().nulls_first(), ContactProfileRow.id.asc())
                .limit(limit)
            )
            rows = list(r.scalars().all())
        return [_row_to_profile(x) for x in rows]

    async def backfill_open_media_from_leads_if_needed(self) -> None:
        """Однократно: перенести open_media из leads в contact_profiles и удалить старые строки."""
        from tender_agents.db import LeadRow, _row_to_lead

        async with self._session_factory() as session:
            meta = await session.execute(
                select(SchemaMetaRow).where(SchemaMetaRow.key == META_KEY_OPEN_MEDIA_MIGRATED)
            )
            if meta.scalar_one_or_none():
                return
            result = await session.execute(select(LeadRow).where(LeadRow.channel == "open_media"))
            rows = list(result.scalars().all())
            if not rows:
                session.add(SchemaMetaRow(key=META_KEY_OPEN_MEDIA_MIGRATED, value="1"))
                await session.commit()
                return
            logger.info("Миграция open_media → contact_profiles: %s записей", len(rows))
            leads = [_row_to_lead(row) for row in rows]
            ids = [row.id for row in rows]
        await self.upsert_open_media_batch(leads)
        async with self._session_factory() as session:
            await session.execute(delete(LeadRow).where(LeadRow.id.in_(ids)))
            session.add(SchemaMetaRow(key=META_KEY_OPEN_MEDIA_MIGRATED, value="1"))
            await session.commit()
