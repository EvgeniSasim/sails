import pytest
from datetime import date
from pydantic import ValidationError
from tender_agents.models import TenderRecord, CollectFilters, CollectPlan
from tender_agents.collect.store import JsonlStore
from tender_agents.platforms.registry import get_adapter
from tender_agents.platforms.sberbank_ast import SberbankAstAdapter
import os
import json

def test_tender_record_validation():
    # Valid record
    record = TenderRecord(
        platform="test",
        title="Test Tender",
        url="https://example.com/1"
    )
    assert record.platform == "test"

    # Missing required field
    with pytest.raises(ValidationError):
        TenderRecord(platform="test", url="https://example.com/1") # missing title

def test_collect_filters_validation():
    filters = CollectFilters(date_from=date(2024, 1, 1))
    assert filters.date_from == date(2024, 1, 1)
    assert filters.date_to is None

def test_registry_matches_url():
    # Ensure Sberbank adapter matches correctly
    adapter = get_adapter("https://www.sberbank-ast.ru/purchaseList.aspx")
    assert isinstance(adapter, SberbankAstAdapter)

    # Non-matching URL
    assert get_adapter("https://google.com") is None

def test_jsonl_store_deduplication(tmp_path):
    file_path = tmp_path / "test.jsonl"
    store = JsonlStore(file_path)

    record1 = TenderRecord(
        platform="sberbank-ast.ru",
        external_id="123",
        title="Tender 1",
        url="https://example.com/1"
    )

    # First write should succeed
    assert store.write(record1) is True

    # Second write of the same record (by platform/external_id) should fail
    record2 = TenderRecord(
        platform="sberbank-ast.ru",
        external_id="123",
        title="Tender 2",
        url="https://example.com/2"
    )
    assert store.write(record2) is False

    # Write by URL if external_id is missing
    record3 = TenderRecord(
        platform="other",
        title="Tender 3",
        url="https://example.com/3"
    )
    assert store.write(record3) is True

    # Same URL should fail
    record4 = TenderRecord(
        platform="another",
        title="Tender 4",
        url="https://example.com/3"
    )
    assert store.write(record4) is False

@pytest.mark.asyncio
async def test_db_store_deduplication(tmp_path):
    from tender_agents.collect.db import DbStore, init_db

    db_file = tmp_path / "test.db"
    db_url = f"sqlite+aiosqlite:///{db_file}"

    await init_db(db_url)
    store = DbStore(db_url)

    record1 = TenderRecord(
        platform="sberbank-ast.ru",
        external_id="DB123",
        title="Tender DB 1",
        url="https://example.com/db1"
    )

    assert await store.write(record1) is True
    assert await store.write(record1) is False # Duplicate

    record2 = TenderRecord(
        platform="sberbank-ast.ru",
        external_id="DB124",
        title="Tender DB 2",
        url="https://example.com/db1" # Same URL
    )
    assert await store.write(record2) is False # Duplicate by URL
