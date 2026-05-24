# Платформенный процесс Osminog (FeedBackTalk)

Краткое руководство для менеджера и агента. Полная спецификация: `prompts/platform-procurement-lpr-osminog.md`.

## Сквозной сценарий

1. **Настройки → Ключи** — вручную или «Сгенерировать ключи из задачи» (агент Keyword Planner).
2. **Настройки → Площадки** — включить `zakupki` (минимум); B2B/Сбер — при Playwright и стабильной сети.
3. **Настройки → Запуск** — указать период (даты или «последние N дней») и запустить пайплайн.
4. **Тендеры** — очередь; **Сделка** (`/deal/{id}`) — тендер + ЛПР + питч.
5. **Контакты / Каналы** — ingest URL рейтинга (kommersant.ru); research по contact_id.
6. **Настройки → Задачи** — связи тендер↔ЛПР, аналитика, разведка новой площадки.
7. **История** (`/analyst`) — отчёт и CSV `/api/tenders/history.csv`.

## CLI (Osminog / cron)

```bash
tender-leads platform keyword-plan "HR опросы госсектор" --save
tender-leads run -s zakupki --period-days 30 --max-per-keyword 15
tender-leads platform link-resolve
tender-leads platform analyst --period-days 90 -o data/analyst_report.json
tender-leads platform scout "https://example-tender.ru/search" --stub
```

## Cron

`scripts/daily-cron.sh` — сбор за 30 дней, экспорт CSV, подсказка для OpenClaw.

## Задачи в БД

Таблица `platform_jobs`: типы `keyword_plan`, `tender_run`, `tender_analyst`, `link_resolve`, `source_scout`, `lpr_research`.
