"""Open-source provenance logging (152-FZ oriented; not legal advice)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column

from tender_agents.orm import Base

logger = logging.getLogger(__name__)

BLOCKED_NETLOCS = {
    "facebook.com",
    "instagram.com",
    "tiktok.com",
}


class DataProvenanceLogRow(Base):
    __tablename__ = "data_provenance_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(Integer, index=True)
    source_url: Mapped[str] = mapped_column(Text)
    field: Mapped[str] = mapped_column(String(64))
    value: Mapped[str] = mapped_column(Text)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


def is_allowed_source_url(url: str) -> bool:
    if not url or not url.strip():
        return False
    try:
        host = (urlparse(url.strip()).hostname or "").lower()
    except Exception:
        return False
    if not host:
        return False
    for blocked in BLOCKED_NETLOCS:
        if host == blocked or host.endswith("." + blocked):
            return False
    return True


class ProvenanceRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession], engine):
        self._session_factory = session_factory
        self._engine = engine

    async def ensure_tables(self) -> None:
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def record_provenance(
        self,
        profile_id: int,
        source_url: str,
        field: str,
        value: str,
        *,
        collected_at: datetime | None = None,
    ) -> None:
        if not is_allowed_source_url(source_url):
            logger.debug("provenance skip blocked url %s", source_url[:80])
            return
        val = (value or "").strip()
        if not val:
            return
        when = collected_at or datetime.now(timezone.utc)
        async with self._session_factory() as session:
            session.add(
                DataProvenanceLogRow(
                    profile_id=profile_id,
                    source_url=source_url[:2000],
                    field=field[:64],
                    value=val[:2000],
                    collected_at=when,
                )
            )
            await session.commit()

    async def list_for_profile(self, profile_id: int, limit: int = 100) -> list[dict]:
        async with self._session_factory() as session:
            q = (
                select(DataProvenanceLogRow)
                .where(DataProvenanceLogRow.profile_id == profile_id)
                .order_by(DataProvenanceLogRow.id.desc())
                .limit(limit)
            )
            rows = (await session.execute(q)).scalars().all()
            return [
                {
                    "source_url": r.source_url,
                    "field": r.field,
                    "value": r.value,
                    "collected_at": r.collected_at.isoformat() if r.collected_at else "",
                }
                for r in rows
            ]
