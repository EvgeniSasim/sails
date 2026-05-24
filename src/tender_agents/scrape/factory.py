from tender_agents.scrape.base import ExtractBackend
from tender_agents.settings import settings


def get_backend(name: str | None = None) -> ExtractBackend:
    backend = (name or settings.scraper_backend).lower().strip()

    if backend in ("scrapegraph", "sgai", "cloud"):
        from tender_agents.scrape.backends.scrapegraph_backend import ScrapeGraphBackend

        return ScrapeGraphBackend()

    if backend in ("crawl4ai", "c4ai"):
        from tender_agents.scrape.backends.crawl4ai_backend import Crawl4AIBackend

        return Crawl4AIBackend()

    if backend in ("playwright", "pw"):
        from tender_agents.scrape.backends.playwright_backend import PlaywrightBackend

        return PlaywrightBackend()

    if backend in ("yandex", "yandexgpt", "aistudio"):
        from tender_agents.scrape.backends.yandex_backend import YandexBackend

        return YandexBackend()

    # default: free httpx
    from tender_agents.scrape.backends.httpx_llm_free import HttpxFreeBackend

    return HttpxFreeBackend()
