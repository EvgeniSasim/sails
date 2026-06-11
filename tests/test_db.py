import pytest
from datetime import datetime
from tender_agents.models import TenderRecord
from tender_agents.collect.db import DbStore, init_db, Tender, SessionLocal
from sqlalchemy import select

@pytest.mark.asyncio
async def test_db_store_write_and_list():
    db_url = "sqlite+aiosqlite:///:memory:"
    await init_db(db_url)
    store = DbStore(db_url)

    record = TenderRecord(
        platform="test.com",
        external_id="123",
        title="Test Tender",
        url="https://test.com/123",
        price="1000",
        matched_keyword="test"
    )

    # Test write
    result = await store.write(record)
    assert result is True

    # Test dedupe
    result_duplicate = await store.write(record)
    assert result_duplicate is False

    # Test list
    records = await store.list_last(limit=10)
    assert len(records) == 1
    assert records[0].external_id == "123"
    assert records[0].platform == "test.com"

@pytest.mark.asyncio
async def test_db_store_dedupe_by_url():
    db_url = "sqlite+aiosqlite:///:memory:"
    await init_db(db_url)
    store = DbStore(db_url)

    record1 = TenderRecord(
        platform="test.com",
        external_id=None,
        title="Test Tender 1",
        url="https://test.com/123",
    )

    record2 = TenderRecord(
        platform="other.com",
        external_id="abc",
        title="Test Tender 2",
        url="https://test.com/123/", # Should normalize and match record1
    )

    await store.write(record1)
    result = await store.write(record2)
    assert result is False
