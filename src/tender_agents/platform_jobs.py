"""Очередь фоновых задач платформы (сбор, ключи, связи, аналитика)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column

from tender_agents.orm import Base

logger = logging.getLogger(__name__)

JOB_TYPES = (
    "keyword_plan",
    "tender_run",
    "lpr_research",
    "link_resolve",
    "tender_analyst",
    "source_scout",
)


class PlatformJobRow(Base):
    __tablename__ = "platform_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_type: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    payload_json: Mapped[str | None] = mapped_column(Text)
    result_json: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


@dataclass
class PlatformJob:
    id: int
    job_type: str
    status: str
    payload: dict[str, Any]
    result: dict[str, Any] | None
    error: str | None
    created_at: datetime | None


class PlatformJobRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession], engine):
        self._session_factory = session_factory
        self._engine = engine

    async def ensure_tables(self) -> None:
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def create(self, job_type: str, payload: dict[str, Any]) -> PlatformJob:
        async with self._session_factory() as session:
            row = PlatformJobRow(
                job_type=job_type,
                status="pending",
                payload_json=json.dumps(payload, ensure_ascii=False),
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return self._row_to_job(row)

    async def update(
        self,
        job_id: int,
        *,
        status: str | None = None,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        async with self._session_factory() as session:
            row = await session.get(PlatformJobRow, job_id)
            if not row:
                return
            if status is not None:
                row.status = status
            if result is not None:
                row.result_json = json.dumps(result, ensure_ascii=False)
            if error is not None:
                row.error = (error or "")[:2000]
            row.updated_at = datetime.now(timezone.utc)
            await session.commit()

    async def get(self, job_id: int) -> PlatformJob | None:
        async with self._session_factory() as session:
            row = await session.get(PlatformJobRow, job_id)
            return self._row_to_job(row) if row else None

    async def list_recent(self, limit: int = 30) -> list[PlatformJob]:
        async with self._session_factory() as session:
            q = (
                select(PlatformJobRow)
                .order_by(PlatformJobRow.id.desc())
                .limit(limit)
            )
            rows = (await session.execute(q)).scalars().all()
            return [self._row_to_job(r) for r in rows]

    @staticmethod
    def _row_to_job(row: PlatformJobRow) -> PlatformJob:
        payload: dict[str, Any] = {}
        result: dict[str, Any] | None = None
        if row.payload_json:
            try:
                payload = json.loads(row.payload_json)
            except json.JSONDecodeError:
                payload = {"raw": row.payload_json[:500]}
        if row.result_json:
            try:
                result = json.loads(row.result_json)
            except json.JSONDecodeError:
                result = {"raw": row.result_json[:500]}
        return PlatformJob(
            id=row.id,
            job_type=row.job_type,
            status=row.status,
            payload=payload,
            result=result,
            error=row.error,
            created_at=row.created_at,
        )


def create_platform_job_repository() -> PlatformJobRepository:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from tender_agents.settings import settings

    url = settings.database_url
    if url.startswith("sqlite"):
        from pathlib import Path

        path_part = url.split("///", 1)[-1] if "///" in url else ""
        if path_part and not path_part.startswith(":"):
            Path(path_part).parent.mkdir(parents=True, exist_ok=True)
    engine = create_async_engine(url, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    return PlatformJobRepository(factory, engine)


def parse_optional_date(s: str | None) -> date | None:
    if not s or not str(s).strip():
        return None
    try:
        return date.fromisoformat(str(s).strip()[:10])
    except ValueError:
        return None
