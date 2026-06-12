import logging
import re
from datetime import date, datetime
from typing import AsyncIterator, Optional, Set
from urllib.parse import urlparse, urlunparse

from tender_agents.browser.exceptions import CaptchaRequiredError
from tender_agents.browser.page_context import (
    capture_main_text,
    click_next_results_page,
    click_search_button,
    dismiss_cookie_banner,
    extract_leaf_listings,
    fill_search_field,
    wait_page_idle,
    wait_search_results,
)
from tender_agents.browser.session import HumanSession
from tender_agents.browser.text_blocks import parse_tender_detail_text
from tender_agents.extract.llm_fallback import extract_tender_from_text, llm_fallback_enabled
from tender_agents.models import CollectFilters, ListingItem, SearchContext, TenderRecord
from tender_agents.platforms.base import PlatformAdapter
from tender_agents.platforms.registry import registry

logger = logging.getLogger(__name__)


def _parse_date(date_str: Optional[str]) -> Optional[date]:
    if not date_str:
        return None
    try:
        clean_date = date_str.split(" ")[0]
        return datetime.strptime(clean_date, "%d.%m.%Y").date()
    except ValueError:
        return None


class SberbankAstAdapter(PlatformAdapter):
    """Адаптер Сбербанк-АСТ: действия по смыслу страницы, данные из leaf-полей и текста."""

    def matches_url(self, url: str) -> bool:
        hostname = urlparse(url).hostname
        if not hostname:
            return False
        return "sberbank-ast.ru" in hostname

    async def _prepare_page(self, session: HumanSession) -> None:
        await wait_page_idle(session.page)
        await dismiss_cookie_banner(session.page)

    async def _check_blocked(self, session: HumanSession) -> None:
        content = await session.page.content()
        if "Вы временно заблокированы" in content or "Request Rejected" in content:
            raise CaptchaRequiredError("Сбербанк-АСТ: временная блокировка или капча")

    async def open_home(self, session: HumanSession):
        await session.goto("https://www.sberbank-ast.ru/")

    async def apply_period_filter(self, session: HumanSession, filters: CollectFilters) -> None:
        if not filters.date_from and not filters.date_to:
            return

        page = session.page
        # Клик по "дополнительные фильтры" для раскрытия полей дат
        expand_btn = page.get_by_text(re.compile(r"дополнительные фильтры", re.I))
        if await expand_btn.count() > 0 and await expand_btn.is_visible():
            logger.debug("Раскрываю дополнительные фильтры")
            await expand_btn.click()
            await session.human_delay()

        # Заполнение дат
        # Поиск полей "Дата публикации с" и "по"
        # Обычно это input рядом с текстом или с соответствующим placeholder
        if filters.date_from:
            date_str = filters.date_from.strftime("%d.%m.%Y")
            logger.info("Устанавливаю фильтр 'Дата публикации с': %s", date_str)
            # Пытаемся найти поле по placeholder или по тексту метки рядом
            from_input = page.get_by_placeholder("ДД.ММ.ГГГГ").first
            # На Сбербанке часто несколько таких полей, нужно более точное позиционирование если возможно
            # Но по ТЗ используем семантику. Если первое поле - это "с", второе - "по".
            if await from_input.count() > 0:
                await from_input.fill(date_str)
                await from_input.press("Enter")

        if filters.date_to:
            date_str = filters.date_to.strftime("%d.%m.%Y")
            logger.info("Устанавливаю фильтр 'Дата публикации по': %s", date_str)
            to_input = page.get_by_placeholder("ДД.ММ.ГГГГ").nth(1)
            if await to_input.count() > 0:
                await to_input.fill(date_str)
                await to_input.press("Enter")

        await session.human_delay()

    async def search(
        self, session: HumanSession, keyword: str, filters: CollectFilters
    ) -> SearchContext:
        search_url = "https://www.sberbank-ast.ru/purchaseList.aspx"
        if session.page.url != search_url:
            await session.goto(search_url)

        await self._prepare_page(session)
        await self._check_blocked(session)

        # Применяем фильтр по датам перед вводом ключевого слова, если даты заданы
        await self.apply_period_filter(session, filters)

        try:
            await fill_search_field(session.page, keyword)
        except Exception:
            await session.check_captcha()
            raise

        await session.human_delay()
        await click_search_button(session.page)

        try:
            await wait_search_results(session.page)
            # Логируем маркер результатов для подтверждения успешного поиска
            text = await capture_main_text(session.page)
            if "Найдено процедур" in text:
                match = re.search(r"Найдено процедур[^\n]*", text)
                if match:
                    logger.info("Статус поиска: %s", match.group(0))
        except Exception:
            logger.warning("Результаты поиска по ключу '%s' не появились вовремя.", keyword)

        return SearchContext(keyword=keyword, filters=filters)

    def _normalize_url(self, url: str) -> str:
        parsed = urlparse(url)
        return urlunparse(
            (
                parsed.scheme,
                parsed.netloc.lower(),
                parsed.path,
                parsed.params,
                parsed.query,
                "",
            )
        )

    async def iter_listing_pages(
        self, session: HumanSession, ctx: SearchContext, max_pages: int
    ) -> AsyncIterator[ListingItem]:
        seen_urls: Set[str] = set()

        for page_num in range(1, max_pages + 1):
            logger.info("Ищу: %s, страница %s", ctx.keyword, page_num)
            await self._prepare_page(session)

            rows = await extract_leaf_listings(session.page)
            if not rows:
                logger.info("Лоты не найдены на текущей странице. Завершаю.")
                break

            found_on_page = 0
            for row in rows:
                raw_url = row["url"]
                norm_url = self._normalize_url(raw_url)
                if norm_url in seen_urls:
                    continue

                seen_urls.add(norm_url)
                found_on_page += 1
                title = row.get("title")
                preview = row.get("preview")
                if row.get("external_id") and preview:
                    preview = f"№ {row['external_id']}\n{preview}"

                yield ListingItem(
                    url=raw_url,
                    title=title.strip() if title else None,
                    preview=preview.strip() if preview else None,
                )

            logger.info("Найдено новых лотов на странице %s: %s", page_num, found_on_page)

            if page_num >= max_pages:
                break

            if not await click_next_results_page(session.page):
                logger.info("Следующая страница недоступна. Конец выдачи.")
                break

            await session.human_delay()
            await session.page.wait_for_load_state("domcontentloaded")
            try:
                await wait_search_results(session.page, timeout_ms=15_000)
            except Exception:
                logger.warning("Выдача не обновилась после пагинации.")

    async def open_detail(
        self,
        session: HumanSession,
        item: ListingItem,
        keyword: str,
        filters: CollectFilters,
    ) -> Optional[TenderRecord]:
        logger.info("Открываю карточку: %s", item.url)
        await session.goto(str(item.url))
        await self._prepare_page(session)
        await session.human_delay()
        await session.page.mouse.wheel(0, 500)
        await session.human_delay(0.5, 1.0)

        text = await capture_main_text(session.page)
        fields = parse_tender_detail_text(text)

        if llm_fallback_enabled(filters.llm_fallback):
            if not fields.get("title") or not fields.get("external_id"):
                llm_fields = await extract_tender_from_text(text, str(item.url))
                for key, value in llm_fields.items():
                    if value and not fields.get(key):
                        fields[key] = value

        external_id = fields.get("external_id")
        if not external_id and item.preview:
            id_match = re.search(r"№\s*([\d-]+)", item.preview)
            if id_match:
                external_id = id_match.group(1)

        publish_date = _parse_date(fields.get("publish_date_str"))
        deadline = _parse_date(fields.get("deadline_str"))

        if publish_date:
            if filters.date_from and publish_date < filters.date_from:
                logger.info("Лот пропущен (дата %s < %s)", publish_date, filters.date_from)
                return None
            if filters.date_to and publish_date > filters.date_to:
                logger.info("Лот пропущен (дата %s > %s)", publish_date, filters.date_to)
                return None

        return TenderRecord(
            platform="sberbank-ast.ru",
            external_id=external_id,
            title=fields.get("title") or item.title or "Без названия",
            url=item.url,
            customer_name=fields.get("customer_name"),
            publish_date=publish_date,
            deadline=deadline,
            price=fields.get("price"),
            matched_keyword=keyword,
            contacts=fields.get("contacts"),
            raw_snippet=item.preview,
        )


registry.register(SberbankAstAdapter())
