import logging
from typing import List, AsyncIterator, Set, Optional
from urllib.parse import urlparse, urljoin, urlunparse
from tender_agents.platforms.base import PlatformAdapter
from tender_agents.browser.session import HumanSession
from tender_agents.platforms.registry import registry
from tender_agents.models import (
    ListingItem,
    CollectFilters,
    SearchContext,
    TenderRecord,
)
from datetime import datetime

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

    async def open_detail(
        self,
        session: HumanSession,
        item: ListingItem,
        keyword: str,
        filters: CollectFilters,
    ) -> Optional[TenderRecord]:
        """Парсинг детальной страницы лота Сбербанк-АСТ."""
        logger.info(f"Открываю карточку: {item.url}")
        await session.page.goto(item.url, wait_until="networkidle")
        await session.human_delay()
        await session.page.mouse.wheel(0, 500)
        await session.human_delay(0.5, 1.0)

        # Извлечение данных из таблицы детальной информации
        # На Сбербанке это часто таблицы с id типа 'BaseMainContent_MainContent_...'
        # Попробуем найти основные поля по текстовым меткам

        async def get_value_by_label(label_text: str) -> Optional[str]:
            # Ищем <td> с текстом метки, затем берем следующий <td>
            xpath = f"//td[contains(text(), '{label_text}')]/following-sibling::td[1]"
            try:
                el = await session.page.query_selector(f"xpath={xpath}")
                if el:
                    text = await el.inner_text()
                    return text.strip()
            except Exception:
                pass
            return None

        external_id = await get_value_by_label("Номер процедуры")
        if not external_id:
            # Альтернативный поиск номера
            external_id = await get_value_by_label("Номер извещения")

        customer_name = await get_value_by_label("Наименование заказчика")
        price = await get_value_by_label("Начальная цена")

        publish_date_str = await get_value_by_label("Дата размещения извещения")
        deadline_str = await get_value_by_label("Дата и время окончания срока подачи заявок")

        def parse_date(date_str: Optional[str]):
            if not date_str:
                return None
            # Формат на Сбербанке обычно: 24.05.2024 10:00:00 (МСК)
            try:
                clean_date = date_str.split(" ")[0]
                return datetime.strptime(clean_date, "%d.%m.%Y").date()
            except Exception:
                return None

        publish_date = parse_date(publish_date_str)
        deadline = parse_date(deadline_str)

        # Проверка фильтра дат
        if publish_date:
            if filters.date_from and publish_date < filters.date_from:
                logger.info(f"Лот пропущен (дата {publish_date} < {filters.date_from})")
                return None
            if filters.date_to and publish_date > filters.date_to:
                logger.info(f"Лот пропущен (дата {publish_date} > {filters.date_to})")
                return None

        contacts = await get_value_by_label("Контактная информация")

        return TenderRecord(
            platform="sberbank-ast.ru",
            external_id=external_id,
            title=item.title or "Без названия",
            url=item.url,
            customer_name=customer_name,
            publish_date=publish_date,
            deadline=deadline,
            price=price,
            matched_keyword=keyword,
            contacts=contacts,
            raw_snippet=item.preview,
        )

# Регистрация адаптера
registry.register(SberbankAstAdapter())
