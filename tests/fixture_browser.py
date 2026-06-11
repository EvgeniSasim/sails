from pathlib import Path
from playwright.async_api import Page as AsyncPage
from playwright.sync_api import Page as SyncPage

def get_fixture_path(name: str) -> Path:
    return Path(__file__).parent / "fixtures" / name

def load_fixture_html(fixture_rel_path: str) -> str:
    path = get_fixture_path(fixture_rel_path)
    return path.read_text(encoding="utf-8")

async def load_fixture_to_page_async(page: AsyncPage, fixture_rel_path: str):
    html = load_fixture_html(fixture_rel_path)
    await page.set_content(html, wait_until="domcontentloaded")

def load_fixture_to_page_sync(page: SyncPage, fixture_rel_path: str):
    html = load_fixture_html(fixture_rel_path)
    page.set_content(html, wait_until="domcontentloaded")
