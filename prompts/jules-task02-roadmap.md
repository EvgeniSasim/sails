# Jules: Задача 2 — надёжный сбор и масштабирование

| | |
|--|--|
| North Star | Стабильный сбор Сбербанк-АСТ, тесты без сети, отчёт для менеджера, второй адаптер |
| Базовое ТЗ | [docs/task-01-spec.md](../docs/task-01-spec.md) §10–11 |
| Стратегия парсинга | [docs/platforms/extraction-strategy.md](../docs/platforms/extraction-strategy.md) |
| Репозиторий Jules | `sources/github/EvgeniSasim/sails` · ветка `main` |
| Правило | **1 сессия Jules = 1 PR = 1 файл** `jules-task-1*.md` |

## Перед первой сессией

В `main` должны быть слои `browser/page_context.py`, `browser/text_blocks.py` и рефактор `platforms/sberbank_ast.py` (leaf + текст, не CSS для данных).

```bash
git push origin main
```

## Порядок (строго по номеру)

| # | Файл | PR-ветка | Зависит от |
|---|------|----------|------------|
| 10 | jules-task-10-extraction-hardening.md | `jules/task02-10-extraction` | main |
| 11 | jules-task-11-offline-fixtures.md | `jules/task02-11-fixtures` | 10 |
| 12 | jules-task-12-period-filter-ui.md | `jules/task02-12-period` | 11 |
| 13 | jules-task-13-collect-report.md | `jules/task02-13-report` | 12 |
| 14 | jules-task-14-resilience.md | `jules/task02-14-resilience` | 13 |
| 15 | jules-task-15-export-csv.md | `jules/task02-15-export` | 14 |
| 16 | jules-task-16-zakupki-adapter.md | `jules/task02-16-zakupki` | 15 |
| 17 | jules-task-17-llm-fallback.md | `jules/task02-17-llm` | 16 |

## Запуск

```bash
export JULES_API_KEY=...
export JULES_SOURCE=sources/github/EvgeniSasim/sails
export JULES_BRANCH=main

# Одна задача:
JULES_TASK=jules-task-10-extraction-hardening.md python3 scripts/jules_create_sessions.py

# Вся цепочка 02 (по одному PR за раз предпочтительнее):
JULES_TASK02=1 python3 scripts/jules_create_sessions.py
```

Трекер: [docs/jules-sessions-task02.md](../docs/jules-sessions-task02.md)
