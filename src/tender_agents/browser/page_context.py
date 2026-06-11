"""Снимок страницы и семантические действия без привязки к CSS-классам."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from playwright.async_api import Page

logger = logging.getLogger(__name__)

_LEAF_VALUE_JS = """(leaf) => {
  const node = document.querySelector(`[content="${leaf}"]`);
  if (!node) return null;
  const value = (node.value ?? node.textContent ?? '').trim();
  return value || null;
}"""

_EXTRACT_LEAF_LISTINGS_JS = """() => {
  const items = [];
  for (const urlNode of document.querySelectorAll('[content="leaf:objectHrefTerm"]')) {
    const root = urlNode.closest('table') || urlNode.closest('tbody') || urlNode.parentElement;
    if (!root) continue;
    const read = (leaf) => {
      const node = root.querySelector(`[content="${leaf}"]`);
      if (!node) return null;
      const value = (node.value ?? node.textContent ?? '').trim();
      return value || null;
    };
    const url = read('leaf:objectHrefTerm');
    if (!url) continue;
    const amount = read('leaf:purchAmount');
    const currency = read('leaf:purchCurrency');
    const text = (root.innerText || '').trim();
    const numMatch = text.match(/№\\s*([\\d-]+)/);
    items.push({
      url,
      title: read('leaf:purchName'),
      external_id: numMatch ? numMatch[1] : null,
      price: [amount, currency].filter(Boolean).join(' ').trim() || null,
      preview: text.slice(0, 500),
    });
  }
  return items;
}"""

_MAIN_TEXT_JS = """() => {
  const root =
    document.querySelector('main') ||
    document.querySelector('[role="main"]') ||
    document.querySelector('#content') ||
    document.body;
  return (root.innerText || '').trim();
}"""

_AJAX_IDLE_JS = """() => {
  const overlay = document.querySelector('#ajax-background');
  if (!overlay) return true;
  const style = window.getComputedStyle(overlay);
  return style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0';
}"""


@dataclass
class PageSnapshot:
    """Компактный снимок страницы для парсинга и отладки."""

    url: str
    main_text: str
    listing_items: list[dict[str, Any]] = field(default_factory=list)
    leaf_fields: dict[str, str] = field(default_factory=dict)

    @property
    def results_marker(self) -> Optional[str]:
        match = re.search(r"Найдено процедур[^\n]*", self.main_text)
        return match.group(0) if match else None


async def wait_page_idle(page: Page, *, timeout_ms: int = 15_000) -> None:
    try:
        await page.wait_for_function(_AJAX_IDLE_JS, timeout=timeout_ms)
    except Exception:
        pass


async def dismiss_cookie_banner(page: Page) -> bool:
    await wait_page_idle(page)
    for name in ("Принять", "Принять все", "Согласен"):
        try:
            button = page.get_by_role("button", name=name, exact=False).first
            if await button.is_visible():
                await button.click(force=True, timeout=3_000)
                return True
        except Exception:
            continue
    try:
        confirm = page.locator("#btnCookieConfirm").first
        if await confirm.count() and await confirm.is_visible():
            await confirm.click(force=True, timeout=3_000)
            return True
    except Exception:
        pass
    return False


async def capture_main_text(page: Page) -> str:
    return await page.evaluate(_MAIN_TEXT_JS)


async def capture_snapshot(page: Page) -> PageSnapshot:
    main_text = await capture_main_text(page)
    listing_items = await extract_leaf_listings(page)
    return PageSnapshot(
        url=page.url,
        main_text=main_text,
        listing_items=listing_items,
    )


async def read_leaf_value(page: Page, leaf: str) -> Optional[str]:
    return await page.evaluate(_LEAF_VALUE_JS, leaf)


async def extract_leaf_listings(page: Page) -> list[dict[str, Any]]:
    rows = await page.evaluate(_EXTRACT_LEAF_LISTINGS_JS)
    return rows or []


async def fill_search_field(page: Page, keyword: str) -> None:
    field = page.get_by_placeholder(re.compile(r"Введите запрос", re.I))
    if await field.count():
        await field.first.fill(keyword)
        return
    # fallback: первое видимое поле поиска рядом с кнопкой «Поиск»
    search_input = page.locator("input[type='text'], input[type='search']").filter(
        has=page.get_by_role("button", name=re.compile(r"Поиск", re.I))
    )
    if await search_input.count():
        await search_input.first.fill(keyword)
        return
    raise RuntimeError("Поле поиска не найдено по placeholder или контексту")


async def click_search_button(page: Page) -> None:
    button = page.get_by_role("button", name=re.compile(r"Поиск", re.I))
    if await button.count():
        await button.first.click()
        return
    raise RuntimeError("Кнопка поиска не найдена по роли и тексту")


async def wait_search_results(page: Page, *, timeout_ms: int = 20_000) -> None:
    try:
        await page.get_by_text(re.compile(r"Найдено процедур", re.I)).first.wait_for(
            timeout=timeout_ms
        )
        return
    except Exception:
        pass
    await page.wait_for_function(
        """() => document.querySelectorAll('[content="leaf:objectHrefTerm"]').length > 0""",
        timeout=timeout_ms,
    )


async def click_next_results_page(page: Page) -> bool:
    next_btn = page.get_by_role("button", name=">", exact=True)
    if await next_btn.count() == 0:
        next_btn = page.locator("span, a, button").filter(has_text=re.compile(r"^>$"))
    if await next_btn.count() == 0:
        return False
    candidate = next_btn.last
    try:
        if not await candidate.is_visible():
            return False
        await candidate.click()
        await wait_page_idle(page)
        return True
    except Exception:
        return False
