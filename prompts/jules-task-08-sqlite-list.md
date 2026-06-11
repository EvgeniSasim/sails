# Jules 08 — SQLite + `list`

**Branch:** `jules/task01-08-sqlite`  
**Depends on:** merge 07

```markdown
You work on JSONL store and TenderRecord model.

## Goal
Optional SQLite persistence + `tender-leads list` to view recent tenders without web UI.

## Read first
- docs/task-01-spec.md step 8
- pyproject.toml — add sqlalchemy, aiosqlite if needed

## Implement
1. Dependencies: `sqlalchemy>=2.0`, `aiosqlite>=0.20`
2. `src/tender_agents/collect/db.py` — async engine, table `tenders` mirroring TenderRecord columns
3. `init_db()` on first collect; upsert same dedupe rules as JSONL
4. After collect, also write to SQLite (or make `--store sqlite|jsonl|both`, default both)
5. CLI `tender-leads list --last 20` — Rich table, Russian headers
6. `.env.example`: `DATABASE_URL=sqlite+aiosqlite:///./data/leads.db`

## Success criteria
```bash
tender-leads collect ...  # saves data
tender-leads list --last 10
```
shows recent rows.

## Do not
- FastAPI dashboard.
```
