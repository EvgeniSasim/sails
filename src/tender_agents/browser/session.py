import asyncio
import logging
import os
import random
from datetime import datetime
from typing import Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from tender_agents.browser.cookies import accept_cookies

logger = logging.getLogger(__name__)

class HumanSession:
    """
    Сессия браузера, имитирующая поведение человека.
    """

    def __init__(self, headed: bool = False):
        self.headed = headed
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.debug_dir = "data/debug"

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=not self.headed)
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="ru-RU",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        self.page = await self.context.new_page()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type and self.page:
            await self.save_screenshot("error")

        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def goto(self, url: str):
        """Переход по URL с последующим принятием cookie."""
        logger.info(f"Открываю {url}...")
        try:
            await self.page.goto(url, wait_until="networkidle")
            await self.human_delay()
            await accept_cookies(self.page)
        except Exception as e:
            logger.error(f"Ошибка при переходе на {url}: {e}")
            await self.save_screenshot("goto_error")
            raise

    async def human_delay(self, min_seconds: float = 0.8, max_seconds: float = 2.5):
        """Случайная задержка для имитации человека."""
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)

    async def save_screenshot(self, prefix: str = "debug"):
        """Сохранение скриншота в data/debug/."""
        os.makedirs(self.debug_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(self.debug_dir, f"{prefix}_{timestamp}.png")
        if self.page:
            await self.page.screenshot(path=filepath)
            logger.info(f"Скриншот сохранен: {filepath}")
        return filepath
