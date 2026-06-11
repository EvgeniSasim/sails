import logging
from playwright.async_api import Page

logger = logging.getLogger(__name__)

async def accept_cookies(page: Page) -> bool:
    """
    Пытается найти и нажать кнопки согласия с cookie (RU/EN).
    Возвращает True, если кнопка была найдена и нажата.
    """
    try:
        await page.wait_for_selector("#ajax-background", state="hidden", timeout=5_000)
    except Exception:
        pass

    try:
        confirm = page.locator("#btnCookieConfirm")
        if await confirm.count() and await confirm.first.is_visible():
            await confirm.first.click(force=True)
            logger.info("Cookie приняты через кнопку: '#btnCookieConfirm'")
            return True
    except Exception:
        pass

    # Список текстов на кнопках (регистронезависимо)
    cookie_buttons = [
        "Принять", "Принять все", "Принять всё", "Согласен", "Я согласен",
        "Accept", "Accept all", "Agree", "OK", "Понятно", "Разрешить", "Allow"
    ]

    found = False
    for text in cookie_buttons:
        try:
            # Ищем кнопку по тексту
            button = page.get_by_role("button", name=text, exact=False)

            # Проверяем первый найденный элемент
            first_button = button.first
            # is_visible() в Python не принимает аргументов
            if await first_button.is_visible():
                await first_button.click()
                logger.info(f"Cookie приняты через кнопку: '{text}'")
                found = True
                break
        except Exception:
            # Игнорируем ошибки при поиске конкретной кнопки
            continue

    if not found:
        logger.debug("Cookie-баннер не найден или кнопки не распознаны")

    return found
