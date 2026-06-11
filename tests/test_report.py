import pytest
import asyncio
from datetime import datetime
from pathlib import Path
from tender_agents.models import CollectPlan, CollectFilters, CollectResult, TenderRecord, ListingItem
from tender_agents.collect.orchestrator import run_collect
from tender_agents.platforms.base import PlatformAdapter
from tender_agents.platforms.registry import registry
import json

class MockAdapter(PlatformAdapter):
    def matches_url(self, url: str) -> bool:
        return "mock.com" in url

    async def open_home(self, session):
        pass

    async def search(self, session, keyword, filters):
        return {"keyword": keyword}

    async def iter_listing_pages(self, session, ctx, max_pages):
        yield ListingItem(url="http://mock.com/1", title="Tender 1")
        yield ListingItem(url="http://mock.com/2", title="Tender 2")
        yield ListingItem(url="http://mock.com/3", title="Tender 3")

    async def open_detail(self, session, item, keyword, filters):
        if "3" in str(item.url):
             raise Exception("Mock error")
        return TenderRecord(
            platform="mock.com",
            external_id=item.url.path.split("/")[-1],
            title=item.title,
            url=item.url,
            matched_keyword=keyword
        )

@pytest.mark.asyncio
async def test_run_collect_stats_and_report(tmp_path):
    # Register mock adapter
    adapter = MockAdapter()
    registry.register(adapter)

    output_path = tmp_path / "test.jsonl"
    report_path = tmp_path / "test-report.json"

    plan = CollectPlan(
        platform_url="http://mock.com",
        keywords=["test"],
        filters=CollectFilters(),
        max_per_keyword=2,
        max_pages=1
    )

    result = await run_collect(
        plan,
        output_path=str(output_path),
        store_type="jsonl"
    )

    # Check stats in result
    assert "test" in result.keyword_stats
    stats = result.keyword_stats["test"]
    assert stats.saved == 2
    assert stats.found_links >= 2
    # Item 3 should cause an error if it was reached, but max_per_keyword=2 might stop it.
    # Let's adjust plan to reach item 3.

    plan.max_per_keyword = 5
    # Fresh output path to avoid duplicates for this part of test
    output_path_2 = tmp_path / "test_2.jsonl"
    result = await run_collect(
        plan,
        output_path=str(output_path_2),
        store_type="jsonl"
    )
    stats = result.keyword_stats["test"]
    assert stats.saved == 2 # 1 and 2 saved, 3 failed
    assert stats.errors == 1
    assert result.errors_count == 1

    # Check report file
    report_path_2 = output_path_2.with_suffix(".json")
    report_path_2 = report_path_2.with_name(report_path_2.stem + "-report.json")
    assert report_path_2.exists()
    with open(report_path_2, "r", encoding="utf-8") as f:
        report = json.load(f)

    assert report["plan"]["keywords"] == ["test"]
    assert report["stats"]["total_saved"] == 2
    assert report["stats"]["total_errors"] == 1
    assert "test" in report["stats"]["per_keyword"]
    assert report["stats"]["per_keyword"]["test"]["saved"] == 2

    # Test deduplication
    # Run again with output_path_2 (which now has records 1 and 2)
    result2 = await run_collect(
        plan,
        output_path=str(output_path_2),
        store_type="jsonl"
    )
    stats2 = result2.keyword_stats["test"]
    assert stats2.saved == 0
    assert stats2.skipped_duplicate == 2
    assert result2.duplicates_count == 2
