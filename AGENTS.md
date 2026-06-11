# AGENTS.md

## Product

Сбор тендеров для **FeedBackTalk** (CX / surveys / HR). Задача 1: менеджер задаёт URL площадки + ключи → браузер как человек (Playwright). ТЗ: `docs/task-01-spec.md`.

## Stack

- Python 3.11+, пакет `src/tender_agents`
- CLI: `tender-leads` (typer)
- Секреты: `.env` (never commit)

## Conventions

- Маленькие шаги, минимальный diff
- Сначала консоль и проверяемый результат, потом UI
- Русские строки в CLI-выводе для менеджера

## Jules

Одна сессия = один файл `prompts/jules-task-01-*.md`. Roadmap: `prompts/jules-task01-roadmap.md`.

```bash
JULES_TASK=jules-task-01-collect-cli.md python3 scripts/jules_create_sessions.py
```

## Run

```bash
pip install -e .
tender-leads status
```
