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
- Цепочка 01 (закрыта): `prompts/jules-task-01-*.md`, трекер `docs/jules-sessions.md`
- Цепочка 02: `prompts/jules-task-10-*.md` … `17`, roadmap `prompts/jules-task02-roadmap.md`, трекер `docs/jules-sessions-task02.md`
- Запуск: `JULES_TASK=jules-task-10-extraction-hardening.md python3 scripts/jules_create_sessions.py`
- PR-ветки: `jules/task01-…`, `jules/task02-…`
