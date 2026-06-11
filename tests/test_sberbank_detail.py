import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from tender_agents.platforms.sberbank_ast import SberbankAstAdapter
from tender_agents.models import ListingItem, CollectFilters

@pytest.mark.asyncio
async def test_open_detail_parsing():
    # Mock session and page
    session = MagicMock()
    session.page = AsyncMock()
    session.human_delay = AsyncMock()

    # Mock element finding
    # labels and their corresponding values
    data = {
        "Номер процедуры": "SBR001-22",
        "Наименование заказчика": "Тестовый Заказчик",
        "Начальная цена": "1 000 000,00 руб.",
        "Дата размещения извещения": "24.05.2024 10:00:00",
        "Дата и время окончания срока подачи заявок": "01.06.2024 18:00:00",
        "Контактная информация": "Иванов Иван, +79991234567"
    }

    async def mock_query_selector(selector):
        if "xpath=" in selector:
            for label, value in data.items():
                if f"contains(text(), '{label}')" in selector:
                    mock_el = AsyncMock()
                    mock_el.inner_text.return_value = value
                    return mock_el
        return None

    session.page.query_selector.side_effect = mock_query_selector

    adapter = SberbankAstAdapter()
    item = ListingItem(url="https://www.sberbank-ast.ru/purchaseview.aspx?id=123", title="Тестовый тендер", preview="Превью")
    filters = CollectFilters()

    record = await adapter.open_detail(session, item, "CRM", filters)

    assert record is not None
    assert record.external_id == "SBR001-22"
    assert record.customer_name == "Тестовый Заказчик"
    assert record.price == "1 000 000,00 руб."
    assert str(record.publish_date) == "2024-05-24"
    assert str(record.deadline) == "2024-06-01"
    assert record.contacts == "Иванов Иван, +79991234567"
    assert record.matched_keyword == "CRM"

@pytest.mark.asyncio
async def test_open_detail_filtering():
    session = MagicMock()
    session.page = AsyncMock()
    session.human_delay = AsyncMock()

    data = {
        "Дата размещения извещения": "10.05.2024 10:00:00",
    }

    async def mock_query_selector(selector):
        if "xpath=" in selector:
            for label, value in data.items():
                if f"contains(text(), '{label}')" in selector:
                    mock_el = AsyncMock()
                    mock_el.inner_text.return_value = value
                    return mock_el
        return None

    session.page.query_selector.side_effect = mock_query_selector

    adapter = SberbankAstAdapter()
    item = ListingItem(url="https://www.sberbank-ast.ru/purchaseview.aspx?id=123", title="Тестовый тендер")

    from datetime import date

    # Filter after the date
    filters = CollectFilters(date_from=date(2024, 5, 11))
    record = await adapter.open_detail(session, item, "CRM", filters)
    assert record is None

    # Filter before the date
    filters = CollectFilters(date_to=date(2024, 5, 9))
    record = await adapter.open_detail(session, item, "CRM", filters)
    assert record is None

    # Filter including the date
    filters = CollectFilters(date_from=date(2024, 5, 1), date_to=date(2024, 5, 20))
    record = await adapter.open_detail(session, item, "CRM", filters)
    assert record is not None
