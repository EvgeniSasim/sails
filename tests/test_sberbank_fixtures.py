import pytest
from playwright.sync_api import Page
from tender_agents.browser.page_context import _EXTRACT_LEAF_LISTINGS_JS, _MAIN_TEXT_JS
from tender_agents.browser.text_blocks import parse_tender_detail_text
from tests.fixture_browser import load_fixture_to_page_sync

def test_leaf_listing_from_fixture(page: Page):
    load_fixture_to_page_sync(page, "sberbank/listing_crm.html")
    items = page.evaluate(_EXTRACT_LEAF_LISTINGS_JS)

    assert len(items) >= 2

    # Check first item
    assert "id=1001" in (items[0]["url"] or "")
    assert "ООО \"Альфа\"" in (items[0]["title"] or "")
    assert items[0]["external_id"] == "01234567890"
    assert "1500000.00 RUB" in (items[0]["price"] or "")

    # Check second item
    assert "id=1002" in (items[1]["url"] or "")
    assert "ПАО \"Бета\"" in (items[1]["title"] or "")
    assert items[1]["external_id"] == "98765432109"
    assert "2300000.00 RUB" in (items[1]["price"] or "")

def test_detail_text_from_fixture(page: Page):
    load_fixture_to_page_sync(page, "sberbank/detail_sample.html")
    main_text = page.evaluate(_MAIN_TEXT_JS)
    fields = parse_tender_detail_text(main_text)

    assert fields["external_id"] == "SBR000-240524-0001"
    assert "поддержке CRM-системы" in fields["title"]
    assert fields["customer_name"] == "ООО \"Сбербанк-Технологии\""
    assert fields["price"] == "500 000,00"
    assert fields["publish_date_str"] == "24.05.2024"
    assert "10.06.2024" in fields["deadline_str"]
