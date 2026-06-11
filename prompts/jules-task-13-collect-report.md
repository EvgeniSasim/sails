# Jules 13 — collect run report

**Branch:** `jules/task02-13-report`  
**Depends on:** merge 12

```markdown
You work on collect orchestrator and CollectResult.

## Goal
After each collect run, manager sees a clear Russian summary and a machine-readable report file.

## Read first
- src/tender_agents/collect/orchestrator.py
- src/tender_agents/models.py (`CollectResult`)
- src/tender_agents/cli.py (`collect` command)

## Implement
1. Extend `CollectResult`:
   - `started_at`, `finished_at` (datetime)
   - `duration_seconds` property
   - `platform_host: str`
   - per-keyword: `found_links`, `saved`, `skipped_duplicate`, `skipped_filter`, `errors`
2. Orchestrator tracks counters during loop (increment on each event)
3. End of `tender-leads collect` — Rich table:
   | Ключ | Сохранено | Дубли | Ошибки | Время |
   Plus totals row
4. Write JSON report alongside jsonl:
   - `data/collect/{date}-{host}-report.json`
   - Include plan params (keywords, dates, limits) + result stats + list of saved external_ids
5. Russian INFO: «Отчёт: data/collect/…-report.json»

## Success criteria
- Offline test: fake adapter run produces expected counts in CollectResult
- After real collect, report JSON exists and matches console totals
- Ctrl+C still writes partial report if any records processed

## Do not
- Web dashboard.
- Change dedup logic in stores (only report what happened).
```
