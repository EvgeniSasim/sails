# Prompt Spec: product-review-sales-managers

| Поле | Значение |
|------|----------|
| ID | `product-review-sales-managers` |
| Версия | 1.0 |
| Этап / Skill | `@prompt-manager` → исполнение `@explore` / Agent |
| Модель / среда | Cursor Agent |
| Язык выхода | русский |
| Продукт | FeedBackTalk — платформа CX / опросов / HR-пульс (tender-lead-agents) |
| Статус | **Устаревший North Star** (CRM-дашборд) — см. `prompts/vision-ai-collection-platform.md` |

## Objective

Пересмотреть репозиторий `/Users/evgenii/Desktop/agents` и выдать **продуктовый и технический план**: инструмент для менеджеров по продажам, который быстро даёт **потенциальных клиентов** — через тендеры и через **ЛПР** (топ-менеджмент, HR, CX, закупки исследований).

## Prompt (готово к копированию)

```markdown
## Role
Ты — product architect + lead engineer. Проект: tender-lead-agents (Python, FastAPI дашборд, SQLite, агенты Search/Enrich/Store).

## North Star (куда идём)
Менеджер за 15–30 минут получает **очередь действий**:
1. **Горячие тендеры** — закупка по теме продукта, дедлайн, заказчик, скор, готовый питч.
2. **ЛПР** — ФИО, должность, компания, где светился, проверенный канал связи, связь с активной закупкой (если есть).
3. **Следующий шаг** — этап воронки, копировать КП, открыть карточку на площадке / написать человеку.

Не цель: «ещё один парсер всего подряд» и автоматический спам из выдачи поисковиков.

## ICP для продаж (кому продаём через инструмент)
- Заказчик тендера: HR, CX, маркетинг, исследования, ИТ-закупка платформы опросов.
- ЛПР из открытых источников: директор по персоналу, CHRO, HRD, директор по клиентскому опыту, руководитель исследований.
- Сегменты уже в коде: hr, cx, research, gov — использовать в плане.

## Context — прочитать в репо
- README.md, config/keywords*.yaml, config/sources.yaml, config/channels.yaml
- src/tender_agents/agents/ (orchestrator, search, enrich, store, contact_research)
- src/tender_agents/web/ (дашборд: тендеры, контакты, воронка, настройки)
- src/tender_agents/contacts_db.py, db.py, scoring.py, pitches.py
- docs/yandex-setup.md

## Task
1. **As-Is**: 1 страница — что уже умеет продукт для менеджера (user journeys по экранам).
2. **Gap**: таблица «ожидание менеджера → сейчас → приоритет (P0/P1/P2)».
3. **To-Be**: 2 потока данных (Тендеры | Люди/компании) и как они сходятся в «карточку сделки».
4. **Roadmap**: 3 фазы (MVP для менеджера / стабильные площадки / обогащение ЛПР).
5. **Backlog**: 10–15 конкретных задач (issue-style), каждая с критерием готово.
6. **Риски**: юридические (152-ФЗ, персональные данные), технич. (капча Яндекс, 404 ЕИС printForm, блокировки).

## Output format
Файл `docs/product-review-sales-managers.md` в репо со структурой:
- Executive summary (5 предложений)
- Personas менеджера
- As-Is / Gap / To-Be
- Roadmap (mermaid допустим)
- Backlog таблица: ID | Задача | P | Effort S/M/L
- Что НЕ делать в v1

## Success criteria
- План привязан к **существующему коду**, не «с нуля на другом стеке».
- P0 включает: понятная очередь «готов к контакту», стабильный zakupki, разделение ключей/пересбор.
- Явно: контакты из СМИ + связь тендер↔контакт + ручная верификация канала перед КП.

## Do not
- Не писать код в этом проходе (только план).
- Не предлагать массовый холодный email из автопарсинга Google/DDG.
- Не включать секреты из .env.
```

## Variables

| Переменная | Пример | Описание |
|------------|--------|----------|
| `{repo}` | `/Users/evgenii/Desktop/agents` | Корень проекта |

## Output contract

- Файл: `docs/product-review-sales-managers.md`
- Executor: новый чат Cursor Agent + `@explore` при необходимости
- Критерий готово: менеджер может прочитать summary и понять «что нажимать завтра»

## Handoff to executor

Executor: Cursor Agent (explore + write doc)  
First read: section «Prompt (готово к копированию)» in this file.

## Changelog

| Дата | Изменение |
|------|-----------|
| 2026-05-20 | v1.0 — старт пересмотра под цель sales managers |

## Review notes

- Источник: запрос пользователя + текущий код tender-lead-agents
