import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock

from tender_agents.models import CollectFilters, ListingItem
from tender_agents.platforms.sberbank_ast import SberbankAstAdapter


def _mock_session(page_text: str):
    session = MagicMock()
    session.human_delay = AsyncMock()
    session.goto = AsyncMock()
    session.page = MagicMock()
    session.page.evaluate = AsyncMock(return_value=page_text)
    session.page.wait_for_function = AsyncMock()
    session.page.wait_for_load_state = AsyncMock()
    session.page.mouse.wheel = AsyncMock()
    session.page.get_by_role = MagicMock(return_value=MagicMock(count=AsyncMock(return_value=0)))
    session.page.get_by_placeholder = MagicMock(return_value=MagicMock(count=AsyncMock(return_value=0)))
    session.page.get_by_text = MagicMock(return_value=MagicMock(first=MagicMock(wait_for=AsyncMock())))
    session.page.locator = MagicMock(return_value=MagicMock(count=AsyncMock(return_value=0)))
    return session


@pytest.mark.asyncio
async def test_open_detail_parsing():
    session = _mock_session("""
    Сведения о закупке № SBR001-22
    Наименование объекта закупки:
    Тестовый тендер
    Начальная (максимальная) цена контракта:
    1 000 000,00 руб.
    Сведения об организаторе торгов:
    Тестовый Заказчик
    Дата и время окончания срока подачи заявок:
    01.06.2024 18:00:00
    Контактная информация:
    Иванов Иван, +79991234567
    24.05.2024 10:00:00 Публикация извещения
    """)

    adapter = SberbankAstAdapter()
    item = ListingItem(
        url="https://www.sberbank-ast.ru/purchaseview.aspx?id=123",
        title="Тестовый тендер",
        preview="Превью",
    )
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
    session = _mock_session("""
    Сведения о закупке № 123
    10.05.2024 10:00:00 Публикация извещения
    """)

    adapter = SberbankAstAdapter()
    item = ListingItem(
        url="https://www.sberbank-ast.ru/purchaseview.aspx?id=123",
        title="Тестовый тендер",
    )

    filters = CollectFilters(date_from=date(2024, 5, 11))
    record = await adapter.open_detail(session, item, "CRM", filters)
    assert record is None

    filters = CollectFilters(date_to=date(2024, 5, 9))
    record = await adapter.open_detail(session, item, "CRM", filters)
    assert record is None

    filters = CollectFilters(date_from=date(2024, 5, 1), date_to=date(2024, 5, 20))
    record = await adapter.open_detail(session, item, "CRM", filters)
    assert record is not None
