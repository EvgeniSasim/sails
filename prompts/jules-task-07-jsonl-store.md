# Jules 07 — JSONL store + dedup

**Branch:** `jules/task01-07-jsonl`  
**Depends on:** merge 06

```markdown
You work on collect orchestrator returning TenderRecord list.

## Goal
Persist collection results to JSON Lines with deduplication.

## Read first
- docs/task-01-spec.md step 7
- src/tender_agents/collect/orchestrator.py

## Implement
1. `src/tender_agents/collect/store.py`:
   - `JsonlStore(path)` append mode
   - dedupe key: `(platform, external_id)` if external_id else normalized `url`
   - load existing keys from file on open
   - `write(record) -> bool` returns False if duplicate skipped
2. Default path: `data/collect/{YYYY-MM-DD}-{platform_host}.jsonl`
3. CLI `--output` optional override
4. Orchestrator calls store after each successful detail
5. Summary: новых / пропущено дублей / ошибок
6. `data/collect/` in .gitignore

## Success criteria
Two consecutive collects with same params do not duplicate URLs in file.
Second run reports «пропущено дублей: N» with N > 0 if first run saved data.

## Do not
- SQLite in this PR.
```
