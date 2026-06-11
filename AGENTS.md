# AGENTS.md

## Product
Сбор тендеров для **FeedBackTalk** (CX / surveys / HR).
Задача 1: Менеджер задаёт URL площадки + ключи → браузер как человек (Playwright).

## Stack
- **Python 3.11+**, пакет `src/tender_agents`
- **CLI**: `tender-leads` (typer + rich)
- **Браузер**: Playwright (Chromium)
- **БД**: SQLite (aiosqlite + sqlalchemy)
- **Валидация**: Pydantic v2

## Conventions
- Маленькие шаги, минимальный diff.
- Сначала консоль и проверяемый результат, потом UI.
- Русские строки в CLI-выводе для менеджера.
- Скриншоты при ошибках в `data/debug/`.
- Логирование с `-v` включает DEBUG уровень, время и уровень сообщения.

## Наблюдаемость
- Если адаптер встречает капчу/блокировку, выбрасывается `CaptchaRequiredError`.
- Лог: «Нужен ручной ввод» + скриншот `data/debug/captcha_*.png`.
- Оркестратор продолжает работу со следующим лотом при ошибке парсинга карточки.

## Тестирование
- `pytest` для офлайн-тестов (валидация, дедупликация, реестр).
- `tender-leads probe-search` для smoke-теста конкретного адаптера.

## Jules
Каждая сессия фиксируется. См. `docs/jules-sessions.md`.
PR-ветки именуются `jules/task...`.
