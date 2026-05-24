# Задачи: Osminog platform (Jules + Cursor Agent)

Спека: `prompts/platform-procurement-lpr-osminog.md` · код: `docs/platform-process-osminog.md`

## Статус (реализовано в репозитории)

| ID | Задача | Файлы |
|----|--------|-------|
| OSM-01 | Период в сборе (zakupki + post-filter) | `orchestrator.py`, `zakupki.py`, UI «Запуск» |
| OSM-02 | Keyword Planner | `agents/keyword_planner_agent.py`, `/settings/keyword-plan` |
| OSM-03 | История + аналитик | `/analyst`, `/api/tenders/history.csv`, `tender_analyst_agent.py` |
| OSM-04 | Registry каналов | `channels/registry.py`, `ingest.py` |
| OSM-05 | Source Scout CLI | `tender-leads platform scout` |
| OSM-06 | Stub адаптера | `source_scout_agent.render_adapter_stub` |
| OSM-07 | Link Resolver | `link_resolver_agent.py`, job `link_resolve` |
| OSM-08 | Карточка сделки | `/deal/{lead_id}` |
| OSM-09 | OpenClaw skill + cron | `skills/tender-leads/SKILL.md`, `scripts/daily-cron.sh` |
| OSM-10 | Очередь задач | `platform_jobs.py`, UI «Задачи» |

## Jules — доработки (если нужно)

1. E2E-тест: `run -s zakupki --period-days 7` с mock HTTP.
2. UI: показ `result_json` завершённых `platform_jobs` на вкладке «Задачи».
3. Авто-подключение `config/sources.d/*.json` в `load_sources()` (сейчас только ручной PR адаптера).
4. Уведомление OpenClaw после job (webhook из `daily-cron.sh`).

## Agent (Cursor) — проверка

```bash
cd /Users/evgenii/Desktop/agents && pip install -e '.[web]' -q
python -c "from tender_agents.platform_job_runner import execute_platform_job; print('ok')"
tender-leads platform keyword-plan "NPS CX" 
```

Перезапуск дашборда: `tender-leads serve --reload`
