import logging
from typing import List, AsyncIterator, Set
from urllib.parse import urlparse, urljoin, urlunparse
from tender_agents.platforms.base import PlatformAdapter
from tender_agents.browser.session import HumanSession
from tender_agents.platforms.registry import registry
from tender_agents.models import ListingItem, CollectFilters, SearchContext

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
    ) -> SearchContext:
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

        # Ожидание загрузки результатов (селектор контейнера лота или сообщения об отсутствии)
        selector_item = ".masterclue"
        selector_empty = "#result-nothing-found" # Гипотетический селектор
        try:
            await session.page.wait_for_selector(f"{selector_item}, {selector_empty}", timeout=15000)
        except Exception:
            logger.warning(f"Результаты поиска по ключу '{keyword}' не появились вовремя.")

        return SearchContext(keyword=keyword, filters=filters)

    def _normalize_url(self, url: str) -> str:
        """Нормализация URL для дедупликации."""
        parsed = urlparse(url)
        # Убираем фрагмент и приводим к нижнему регистру хост
        # Для Сбербанка обычно важен query param id или аналогичный,
        # но пока оставим базовую нормализацию.
        return urlunparse((
            parsed.scheme,
            parsed.netloc.lower(),
            parsed.path,
            parsed.params,
            parsed.query,
            ""
        ))

    async def iter_listing_pages(
        self, session: HumanSession, ctx: SearchContext, max_pages: int
    ) -> AsyncIterator[ListingItem]:
        seen_urls: Set[str] = set()
        base_url = "https://www.sberbank-ast.ru"

        for page_num in range(1, max_pages + 1):
            logger.info(f"Парсинг страницы {page_num} для ключа '{ctx.keyword}'...")

            selector_item = ".masterclue"
            items = await session.page.query_selector_all(selector_item)

            if not items:
                logger.info("Лоты не найдены на текущей странице. Завершаю.")
                break

            found_on_page = 0
            for item in items:
                # Ссылка на детальную страницу
                link_el = await item.query_selector("a[href*='purchaseview']")
                if not link_el:
                    continue

                href = await link_el.get_attribute("href")
                raw_url = urljoin(base_url, href)
                norm_url = self._normalize_url(raw_url)

                if norm_url in seen_urls:
                    continue

                seen_urls.add(norm_url)
                found_on_page += 1

                # Заголовок
                title_el = await item.query_selector(".es-el-name")
                title = await title_el.inner_text() if title_el else None

                # Превью
                preview = await item.inner_text()

                yield ListingItem(
                    url=raw_url,
                    title=title.strip() if title else None,
                    preview=preview.strip() if preview else None
                )

            logger.info(f"Найдено новых лотов на странице {page_num}: {found_on_page}")

            if page_num < max_pages:
                # Попытка перехода на следующую страницу
                # Селектор для кнопки "Следующая" в ASP.NET GridView обычно содержит pager и конкретные стили или текст
                # На Сбербанке это часто <a> с текстом ">" внутри пейджера
                next_btn = await session.page.query_selector("td.pager-btns a:has-text('>')")
                if not next_btn:
                    # Попробуем альтернативный вариант - поиск по номеру следующей страницы
                    next_btn = await session.page.query_selector(f"td.pager-btns a:has-text('{page_num + 1}')")

                if next_btn:
                    logger.info(f"Переход на страницу {page_num + 1}...")
                    await next_btn.click()
                    await session.human_delay()
                    # Ждем обновления контента (можно ждать исчезновения старых элементов или появления новых)
                    await session.page.wait_for_load_state("networkidle")
                else:
                    logger.info("Кнопка следующей страницы не найдена. Конец выдачи.")
                    break

# Регистрация адаптера
registry.register(SberbankAstAdapter())
