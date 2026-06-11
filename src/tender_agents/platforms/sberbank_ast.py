import logging
from typing import List
from urllib.parse import urlparse, urljoin
from tender_agents.platforms.base import PlatformAdapter
from tender_agents.browser.session import HumanSession
from tender_agents.platforms.registry import registry
from tender_agents.models import ListingItem, CollectFilters

logger = logging.getLogger(__name__)

class SberbankAstAdapter(PlatformAdapter):
    """Адаптер для площадки Сбербанк-АСТ (sberbank-ast.ru)."""

    def matches_url(self, url: str) -> bool:
        hostname = urlparse(url).hostname
        if not hostname:
            return False
        return "sberbank-ast.ru" in hostname

    async def open_home(self, session: HumanSession):
        await session.goto("https://www.sberbank-ast.ru/")

    async def search(
        self, session: HumanSession, keyword: str, filters: CollectFilters
    ) -> List[ListingItem]:
        # Переход на страницу поиска, если мы еще не там
        search_url = "https://www.sberbank-ast.ru/purchaseList.aspx"
        if session.page.url != search_url:
            await session.goto(search_url)

        # Заполнение поля поиска
        selector_input = "input#txtKeyword"
        await session.page.wait_for_selector(selector_input, timeout=10000)
        await session.page.fill(selector_input, keyword)
        await session.human_delay()

        # Клик по кнопке поиска
        selector_btn = "input#btnSearch"
        await session.page.click(selector_btn)

        # Ожидание загрузки результатов (селектор контейнера лота)
        selector_item = ".masterclue"
        try:
            await session.page.wait_for_selector(selector_item, timeout=15000)
        except Exception:
            logger.warning(f"Результаты поиска по ключу '{keyword}' не найдены или страница долго грузится.")
            return []

        # Парсинг результатов
        items = await session.page.query_selector_all(selector_item)
        results = []

        base_url = "https://www.sberbank-ast.ru"

        for item in items:
            # Ссылка на детальную страницу
            link_el = await item.query_selector("a[href*='purchaseview']")
            if not link_el:
                continue

            href = await link_el.get_attribute("href")
            url = urljoin(base_url, href)

            # Заголовок
            title_el = await item.query_selector(".es-el-name")
            title = await title_el.inner_text() if title_el else None

            # Превью (можно взять весь текст элемента или его часть)
            preview = await item.inner_text()

            results.append(ListingItem(
                url=url,
                title=title.strip() if title else None,
                preview=preview.strip() if preview else None
            ))

        return results

# Регистрация адаптера
registry.register(SberbankAstAdapter())
