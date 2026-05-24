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

## Cron (ежедневно 08:00)

`scripts/daily-cron.sh` — настройте путь в crontab или скопируйте `scripts/com.openclaw.tender-leads.plist.example` в LaunchAgents.

## OpenClaw

После cron отправьте пользователю краткий отчёт:

> Собрано N лидов по опросам. Новые: … CSV: data/leads_YYYYMMDD.csv

Можно вызвать `tender-leads list` и прикрепить топ-5 заказчиков.
