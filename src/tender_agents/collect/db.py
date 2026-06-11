import logging
from datetime import datetime, date
from typing import Optional, List

from sqlalchemy import String, Date, DateTime, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from tender_agents.models import TenderRecord

logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

class Tender(Base):
    __tablename__ = "tenders"

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(255), index=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(1000))
    url: Mapped[str] = mapped_column(String(1000), index=True, unique=True)
    customer_name: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    publish_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    deadline: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    price: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    matched_keyword: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contacts: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    raw_snippet: Mapped[Optional[str]] = mapped_column(String(4000), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

engine = None
SessionLocal = None

async def init_db(db_url: str):
    global engine, SessionLocal
    engine = create_async_engine(db_url)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

class DbStore:
    def __init__(self, db_url: str):
        self.db_url = db_url

    async def write(self, record: TenderRecord) -> bool:
        if SessionLocal is None:
            await init_db(self.db_url)

        async with SessionLocal() as session:
            async with session.begin():
                # Check for existing record
                # Same dedupe logic as JsonlStore: (platform, external_id) or URL
                url_str = str(record.url).rstrip("/")

                stmt = select(Tender)
                if record.external_id:
                    stmt = stmt.where(
                        ((Tender.platform == record.platform) & (Tender.external_id == record.external_id)) |
                        (Tender.url == url_str)
                    )
                else:
                    stmt = stmt.where(Tender.url == url_str)

                result = await session.execute(stmt)
                existing = result.scalars().first()

                if existing:
                    return False

                # Insert new record
                new_tender = Tender(
                    platform=record.platform,
                    external_id=record.external_id,
                    title=record.title,
                    url=url_str,
                    customer_name=record.customer_name,
                    publish_date=record.publish_date,
                    deadline=record.deadline,
                    price=record.price,
                    matched_keyword=record.matched_keyword,
                    contacts=record.contacts,
                    raw_snippet=record.raw_snippet,
                    collected_at=record.collected_at,
                )
                session.add(new_tender)
                return True

    async def list_last(self, limit: int = 20, platform: Optional[str] = None) -> List[Tender]:
        if SessionLocal is None:
            await init_db(self.db_url)

        async with SessionLocal() as session:
            stmt = select(Tender).order_by(Tender.collected_at.desc()).limit(limit)
            if platform:
                stmt = stmt.where(Tender.platform == platform)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_tender(self, external_id: Optional[str] = None, url: Optional[str] = None) -> Optional[Tender]:
        if SessionLocal is None:
            await init_db(self.db_url)

        async with SessionLocal() as session:
            stmt = select(Tender)
            if external_id:
                stmt = stmt.where(Tender.external_id == external_id)
            elif url:
                stmt = stmt.where(Tender.url == url.rstrip("/"))
            else:
                return None

            result = await session.execute(stmt)
            return result.scalars().first()
