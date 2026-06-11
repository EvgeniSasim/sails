# Jules: Задача 1 — сбор тендеров (пошагово)

| | |
|--|--|
| North Star | [docs/task-01-spec.md](../docs/task-01-spec.md) |
| Репозиторий Jules | `sources/github/EvgeniSasim/sails` · ветка `main` |
| Правило | **1 сессия Jules = 1 PR = 1 файл** `jules-task-01-*.md` |

## Перед первой сессией

Локальный каркас v0.2.0 должен быть в `main` на GitHub (после wipe старого кода):

```bash
git add -A && git commit -m "..." && git push origin main
```

Jules читает код с GitHub, не с вашего диска, пока не смержите PR.

## Порядок (строго по номеру)

| # | Файл | PR-ветка | Зависит от |
|---|------|----------|------------|
| 01 | jules-task-01-collect-cli.md | `jules/task01-01-collect-cli` | каркас main |
| 02 | jules-task-02-browser-session.md | `jules/task01-02-browser` | 01 |
| 03 | jules-task-03-sberbank-search.md | `jules/task01-03-sber-search` | 02 |
| 04 | jules-task-04-sberbank-pagination.md | `jules/task01-04-pagination` | 03 |
| 05 | jules-task-05-sberbank-detail.md | `jules/task01-05-detail` | 04 |
| 06 | jules-task-06-orchestrator.md | `jules/task01-06-orchestrator` | 05 |
| 07 | jules-task-07-jsonl-store.md | `jules/task01-07-jsonl` | 06 |
| 08 | jules-task-08-sqlite-list.md | `jules/task01-08-sqlite` | 07 |
| 09 | jules-task-09-observability.md | `jules/task01-09-observability` | 08 |

## Запуск

```bash
export JULES_API_KEY=...
export JULES_SOURCE=sources/github/EvgeniSasim/sails
export JULES_BRANCH=main

# Одна задача:
JULES_TASK=jules-task-01-collect-cli.md python3 scripts/jules_create_sessions.py

# Вся цепочка (лучше по 1 за раз, после merge предыдущего):
JULES_TASK01=1 python3 scripts/jules_create_sessions.py
```

Трекер сессий: [docs/jules-sessions.md](../docs/jules-sessions.md)
