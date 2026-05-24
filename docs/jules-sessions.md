# Jules sessions (2026-05-20)

Источник: `sources/github/EvgeniSasim/sails` (ветка `main`).

| # | Задача | Session ID | Статус |
|---|--------|------------|--------|
| 1 | zakupki-resilience | — | **400 FAILED_PRECONDITION** (лимит/конфликт; повторить вручную) |
| 2 | research-captcha-compliance | `11039565428354772031` | создана |
| 3 | excel-import | `875956085978133483` | влито в `main` (`excel_ingest`, PR #1 закрыт); fix path traversal — `b295ae6` ≈ наш UUID + resolve |

Повтор задачи 1:

```bash
set -a && source /Users/evgenii/business/.env && export JULES_SOURCE=sources/github/EvgeniSasim/sails
python3 scripts/jules_create_sessions.py  # только zakupki — отредактировать order в скрипте
```

Локально задача 1 уже закрыта (zakupki + `tests/test_zakupki_urls.py`).

Просмотр: https://jules.google.com
