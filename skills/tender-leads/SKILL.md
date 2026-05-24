---
name: tender-leads
description: Сбор лидов с zakupki.gov.ru и других площадок закупок. Бесплатный режим по умолчанию (httpx).
---

# Tender Leads

## Бесплатный режим (рекомендуется)

```bash
export SCRAPER_BACKEND=httpx
tender-leads run -s zakupki -k "проведение онлайн опросов" --max-per-keyword 10
tender-leads list
tender-leads serve   # http://127.0.0.1:8765
```

ЕИС (zakupki) парсится **без API-ключей** — нативный HTML-парсер.

## B2B / Сбербанк-АСТ (нужен JS)

```bash
pip install -e '.[playwright]'
playwright install chromium
tender-leads run -s b2b_center -b playwright --max-per-keyword 5
```

## Альтернатива ScrapeGraphAI — Crawl4AI + Ollama

```bash
ollama pull llama3.2
pip install -e '.[crawl4ai]'
tender-leads run -s b2b_center -b crawl4ai
```

## Yandex AI Studio

```bash
pip install -e '.[yandex]'
# YANDEX_API_KEY + YANDEX_FOLDER_ID в .env
tender-leads yandex check
tender-leads yandex run -s zakupki --keywords-only -k "онлайн опрос"
```

## Платный облачный вариант

```bash
export SGAI_API_KEY=...
tender-leads run -b scrapegraph
```

## Платформенный процесс (Osminog)

```bash
# Ключи из задачи менеджера
tender-leads platform keyword-plan "HR eNPS госсектор" --save --merge-hr-cx

# Сбор с периодом (ЕИС publishDate + фильтр после enrich)
tender-leads run -s zakupki --period-days 30 --max-per-keyword 15

# Связи тендер ↔ ЛПР, аналитика, новая площадка
tender-leads platform link-resolve
tender-leads platform analyst --period-days 90 -o data/analyst_report.json
tender-leads platform scout "https://…" --save --stub
```

Дашборд: **Настройки → Запуск** (период), **Ключи** (агент), **Задачи** (очередь), **История** `/analyst`, сделка `/deal/{id}`.

Документация: `docs/platform-process-osminog.md`.

## Cron (ежедневно 08:00)

`scripts/daily-cron.sh` — сбор за 30 дней, экспорт CSV, связи ЛПР, подсказка для отчёта.

## OpenClaw

После cron отправьте пользователю краткий отчёт:

> Собрано N лидов за 30 дней. Скор ≥60: M. CSV: data/leads_YYYYMMDD.csv
> Связи тендер↔ЛПР пересобраны. Топ заказчиков: … (из `tender-leads platform analyst --period-days 7`)

Можно вызвать `tender-leads list --min-score 60` и открыть `/queue` в дашборде.
