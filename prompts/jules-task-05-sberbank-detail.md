# Jules 05 — tender detail extraction

**Branch:** `jules/task01-05-detail`  
**Depends on:** merge 04

```markdown
You work on SberbankAstAdapter with listing + pagination.

## Goal
Open each tender card and extract structured `TenderRecord` fields.

## Read first
- docs/task-01-spec.md §4 (TenderRecord fields)
- src/tender_agents/platforms/sberbank_ast.py

## Implement
1. Extend `models.py` — `TenderRecord` pydantic model per spec:
   platform, external_id, title, url, customer_name, publish_date, deadline, price, matched_keyword, contacts, raw_snippet, collected_at
2. `open_detail(session, item, keyword) -> TenderRecord` on adapter
3. Navigate like human: goto URL or click row, wait load, scroll, human_delay
4. Parse fields from detail DOM; tolerate missing optional fields
5. If `CollectFilters` date range set: skip records outside range when publish_date known
6. Respect `max_per_keyword` when driven from probe CLI:
   `probe-search --fetch-details --max-per-keyword 5` prints JSON lines or Rich table

## Success criteria
Fetch 5 details: at least title + url + (external_id OR customer_name) populated for majority.
Russian log per card: «Карточка 3/5: {title[:60]}…»

## Do not
- Multi-keyword orchestrator (next PR).
- SQLite yet.
```
