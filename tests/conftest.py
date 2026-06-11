import pytest
from playwright.sync_api import Page, sync_playwright


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser) -> Page:
    context = browser.new_context(locale="ru-RU")
    page = context.new_page()
    yield page
    context.close()
