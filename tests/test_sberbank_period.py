import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import date
import re
from tender_agents.platforms.sberbank_ast import SberbankAstAdapter
from tender_agents.models import CollectFilters

@pytest.mark.asyncio
async def test_apply_period_filter_calls_playwright():
    adapter = SberbankAstAdapter()

    # Mock HumanSession and Page
    session = MagicMock()
    page = MagicMock() # Use MagicMock for page, locators will be AsyncMocks
    session.page = page
    session.human_delay = AsyncMock()

    filters = CollectFilters(
        date_from=date(2025, 1, 1),
        date_to=date(2025, 1, 31)
    )

    # Mock locators
    expand_btn = AsyncMock()
    expand_btn.count = AsyncMock(return_value=1)
    expand_btn.is_visible = AsyncMock(return_value=True)
    page.get_by_text.return_value = expand_btn

    date_input = MagicMock()
    page.get_by_placeholder.return_value = date_input

    # Mock first() and nth() to return different mocks or same mock
    from_input = AsyncMock()
    from_input.count = AsyncMock(return_value=1)
    to_input = AsyncMock()
    to_input.count = AsyncMock(return_value=1)

    date_input.first = from_input
    date_input.nth.return_value = to_input

    await adapter.apply_period_filter(session, filters)

    # Verify "дополнительные фильтры" was clicked
    page.get_by_text.assert_called_with(re.compile(r"дополнительные фильтры", re.I))
    expand_btn.click.assert_called_once()

    # Verify date_from was filled
    page.get_by_placeholder.assert_called_with("ДД.ММ.ГГГГ")
    from_input.fill.assert_called_once_with("01.01.2025")
    from_input.press.assert_called_once_with("Enter")

    # Verify date_to was filled
    to_input.fill.assert_called_once_with("31.01.2025")
    to_input.press.assert_called_once_with("Enter")

@pytest.mark.asyncio
async def test_apply_period_filter_no_dates():
    adapter = SberbankAstAdapter()
    session = MagicMock()
    filters = CollectFilters()

    await adapter.apply_period_filter(session, filters)

    # Should return early and not touch the page
    assert not session.page.called

@pytest.mark.asyncio
async def test_search_calls_apply_period_filter():
    adapter = SberbankAstAdapter()
    adapter.apply_period_filter = AsyncMock()
    adapter._prepare_page = AsyncMock()
    adapter._check_blocked = AsyncMock()

    session = MagicMock()
    session.page.url = "https://www.sberbank-ast.ru/purchaseList.aspx"
    session.human_delay = AsyncMock()
    session.check_captcha = AsyncMock()

    filters = CollectFilters(date_from=date(2025, 1, 1))

    from unittest.mock import patch
    with patch("tender_agents.platforms.sberbank_ast.fill_search_field", AsyncMock()),          patch("tender_agents.platforms.sberbank_ast.click_search_button", AsyncMock()),          patch("tender_agents.platforms.sberbank_ast.wait_search_results", AsyncMock()),          patch("tender_agents.platforms.sberbank_ast.capture_main_text", AsyncMock(return_value="")):

        await adapter.search(session, "keyword", filters)

    adapter.apply_period_filter.assert_called_once_with(session, filters)
