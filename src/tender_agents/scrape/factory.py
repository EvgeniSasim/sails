import logging

from tender_agents.scrape.base import ExtractBackend
from tender_agents.settings import settings

logger = logging.getLogger(__name__)

_YANDEX_BACKEND_NAMES = frozenset({"yandex", "yandexgpt", "aistudio"})


def get_backend(name: str | None = None) -> ExtractBackend:
    backend = (name or settings.scraper_backend).lower().strip()

    if backend in _YANDEX_BACKEND_NAMES:
        from tender_agents.yandex.config import is_yandex_configured

        if not is_yandex_configured():
            logger.warning(
                "Бэкенд yandex выбран, но YANDEX_API_KEY или Folder ID не заданы — используется httpx"
            )
            backend = "httpx"

    if backend in ("scrapegraph", "sgai", "cloud"):
        from tender_agents.scrape.backends.scrapegraph_backend import ScrapeGraphBackend

        return ScrapeGraphBackend()

    if backend in ("crawl4ai", "c4ai"):
        from tender_agents.scrape.backends.crawl4ai_backend import Crawl4AIBackend

        return Crawl4AIBackend()

    if backend in ("playwright", "pw"):
        from tender_agents.scrape.backends.playwright_backend import (
            PlaywrightBackend,
            playwright_installed,
        )

        if not playwright_installed():
            logger.warning(
                "Playwright не установлен (pip install -e '.[playwright]' && "
                "playwright install chromium) — используется httpx; "
                "b2b_center/sberbank_ast — нативные парсеры"
            )
            backend = "httpx"
        else:
            return PlaywrightBackend()

    if backend in ("yandex", "yandexgpt", "aistudio"):
        from tender_agents.scrape.backends.yandex_backend import YandexBackend

        return YandexBackend()

    # default: free httpx
    from tender_agents.scrape.backends.httpx_llm_free import HttpxFreeBackend

    return HttpxFreeBackend()
