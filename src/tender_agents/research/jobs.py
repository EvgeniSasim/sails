"""SQLite-backed contact research jobs."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column

from tender_agents.orm import Base

logger = logging.getLogger(__name__)

JOB_STATUSES = (
    "pending",
    "running",
    "needs_captcha",
    "needs_manual",
    "completed",
    "failed",
)


class ContactResearchJobRow(Base):
    __tablename__ = "contact_research_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    query: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    error: Mapped[str | None] = mapped_column(Text)
    result_json: Mapped[str | None] = mapped_column(Text)
    challenge_url: Mapped[str | None] = mapped_column(Text)
    search_engine: Mapped[str | None] = mapped_column(String(64))
    instructions: Mapped[str | None] = mapped_column(Text)


@dataclass
class ContactResearchJob:
    id: int
    profile_id: int
    status: str
    query: str
    created_at: datetime | None
    error: str | None = None
    result: dict[str, Any] | None = None
    challenge_url: str | None = None
    search_engine: str | None = None
    instructions: str | None = None


def _row_to_job(row: ContactResearchJobRow) -> ContactResearchJob:
    result = None
    if row.result_json:
        try:
            result = json.loads(row.result_json)
        except json.JSONDecodeError:
            result = {"raw": row.result_json[:500]}
    return ContactResearchJob(
        id=row.id,
        profile_id=row.profile_id,
        status=row.status,
        query=row.query or "",
        created_at=row.created_at,
        error=row.error,
        result=result,
        challenge_url=row.challenge_url,
        search_engine=row.search_engine,
        instructions=row.instructions,
    )


class ResearchJobRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession], engine):
        self._session_factory = session_factory
        self._engine = engine

    async def ensure_tables(self) -> None:
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def create_job(self, profile_id: int, query: str) -> ContactResearchJob:
        async with self._session_factory() as session:
            row = ContactResearchJobRow(
                profile_id=profile_id,
                status="pending",
                query=query[:2000],
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return _row_to_job(row)

    async def get_job(self, job_id: int) -> ContactResearchJob | None:
        async with self._session_factory() as session:
            row = await session.get(ContactResearchJobRow, job_id)
            return _row_to_job(row) if row else None

    async def latest_for_profile(self, profile_id: int) -> ContactResearchJob | None:
        async with self._session_factory() as session:
            q = (
                select(ContactResearchJobRow)
                .where(ContactResearchJobRow.profile_id == profile_id)
                .order_by(ContactResearchJobRow.id.desc())
                .limit(1)
            )
            row = (await session.execute(q)).scalar_one_or_none()
            return _row_to_job(row) if row else None

    async def update_job(
        self,
        job_id: int,
        *,
        status: str | None = None,
        error: str | None = None,
        result: dict | None = None,
        challenge_url: str | None = None,
        search_engine: str | None = None,
        instructions: str | None = None,
    ) -> None:
        async with self._session_factory() as session:
            row = await session.get(ContactResearchJobRow, job_id)
            if not row:
                return
            if status:
                row.status = status
            if error is not None:
                row.error = error[:4000] if error else None
            if result is not None:
                row.result_json = json.dumps(result, ensure_ascii=False)[:50000]
            if challenge_url is not None:
                row.challenge_url = challenge_url[:2000] if challenge_url else None
            if search_engine is not None:
                row.search_engine = search_engine[:64] if search_engine else None
            if instructions is not None:
                row.instructions = instructions[:4000] if instructions else None
            row.updated_at = datetime.now(timezone.utc)
            await session.commit()

    async def list_needs_captcha(self, limit: int = 50) -> list[ContactResearchJob]:
        async with self._session_factory() as session:
            q = (
                select(ContactResearchJobRow)
                .where(
                    ContactResearchJobRow.status.in_(("needs_captcha", "needs_manual"))
                )
                .order_by(ContactResearchJobRow.id.desc())
                .limit(limit)
            )
            rows = (await session.execute(q)).scalars().all()
            return [_row_to_job(r) for r in rows]
