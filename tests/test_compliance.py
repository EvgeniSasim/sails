import pytest

from tender_agents.compliance import is_allowed_source_url


def test_blocks_facebook():
    assert is_allowed_source_url("https://www.facebook.com/page") is False


def test_allows_public_site():
    assert is_allowed_source_url("https://example.com/team") is True


@pytest.mark.asyncio
async def test_provenance_write(tmp_path, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from tender_agents.compliance import ProvenanceRepository
    from tender_agents.orm import Base

    db_path = tmp_path / "t.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    repo = ProvenanceRepository(factory, engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await repo.record_provenance(1, "https://kommersant.ru/doc/1", "email", "a@b.ru")
    rows = await repo.list_for_profile(1)
    assert len(rows) == 1
    assert rows[0]["field"] == "email"
