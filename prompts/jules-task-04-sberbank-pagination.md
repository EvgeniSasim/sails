# Jules 04 — listing pagination

**Branch:** `jules/task01-04-pagination`  
**Depends on:** merge 03

```markdown
You work on SberbankAstAdapter with working single-page search.

## Goal
Iterate listing pages up to `--max-pages`, dedupe URLs within one keyword search.

## Read first
- docs/platforms/sberbank-ast.md
- src/tender_agents/platforms/sberbank_ast.py
- docs/task-01-spec.md step 4

## Implement
1. Change search flow to return `SearchContext` (keyword, filters, first page state) if cleaner.
2. `iter_listing_pages(session, ctx, max_pages) -> Iterator[ListingItem]` on adapter or helper.
3. Click «next» / page numbers with human_delay between pages.
4. Dedupe by normalized URL in memory.
5. Optional: apply period filter in UI if Sberbank exposes it; document in sberbank-ast.md. If not available, note «фильтр периода — на шаге detail».
6. Wire `probe-search` (or collect plan) to accept `--max-pages` and report unique count.

## Success criteria
```
tender-leads probe-search --platform-url https://www.sberbank-ast.ru/ -k "закупка" --max-pages 2 -v
```
prints unique URL count ≥ items on page 1; no duplicates between pages.

## Do not
- Open tender detail cards yet.
- Parallel browser tabs.
```
