import pytest
from unittest.mock import AsyncMock, MagicMock
from tender_agents.browser.page_context import capture_snapshot, extract_leaf_listings, PageSnapshot

@pytest.mark.asyncio
async def test_extract_leaf_listings_mock():
    mock_page = MagicMock()
    # Simulate the JS returning a list of items
    mock_items = [
        {
            "url": "https://example.com/1",
            "title": "Tender 1",
            "external_id": "123",
            "price": "1000 RUB",
            "preview": "Preview 1"
        }
    ]
    mock_page.evaluate = AsyncMock(return_value=mock_items)

    items = await extract_leaf_listings(mock_page)
    assert items == mock_items
    assert mock_page.evaluate.called

@pytest.mark.asyncio
async def test_capture_snapshot_mock():
    mock_page = MagicMock()
    mock_page.url = "https://example.com/list"

    # We need to mock both evaluates inside capture_snapshot
    # One for main_text, one for leaf_listings
    mock_page.evaluate = AsyncMock()
    mock_page.evaluate.side_effect = [
        "Найдено процедур 10\nMain content", # _MAIN_TEXT_JS
        [{"url": "item1"}] # _EXTRACT_LEAF_LISTINGS_JS
    ]

    snap = await capture_snapshot(mock_page)

    assert snap.url == "https://example.com/list"
    assert "Main content" in snap.main_text
    assert snap.listing_items == [{"url": "item1"}]
    assert snap.results_marker == "Найдено процедур 10"

def test_page_snapshot_results_marker():
    snap = PageSnapshot(
        url="http://test.com",
        main_text="Some header\nНайдено процедур 123 на странице\nFooter",
        listing_items=[]
    )
    assert snap.results_marker == "Найдено процедур 123 на странице"

    snap_no_marker = PageSnapshot(
        url="http://test.com",
        main_text="No results here",
        listing_items=[]
    )
    assert snap_no_marker.results_marker is None
