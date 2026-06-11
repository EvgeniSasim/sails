# Jules 10 — extraction layer hardening

**Branch:** `jules/task02-10-extraction`  
**Depends on:** main (page_context + text_blocks merged)

```markdown
You work on tender-leads v0.2.0 with Playwright collect pipeline for Sberbank-AST.

## Goal
Harden the page-context extraction layer: tests, debug CLI, docs — no CSS selectors for **data** in sberbank adapter.

## Read first
- docs/platforms/extraction-strategy.md
- src/tender_agents/browser/page_context.py
- src/tender_agents/browser/text_blocks.py
- src/tender_agents/platforms/sberbank_ast.py

## Implement
1. Ensure `SberbankAstAdapter` uses only:
   - `page_context` for actions (placeholder, role, leaf fields, text markers)
   - `text_blocks.parse_tender_detail_text` for detail fields
   - No `#id` / `.class` selectors in adapter for parsing listing/detail data
2. Add unit tests:
   - `tests/test_page_context.py` — mock `page.evaluate` for leaf listing JS shape
   - Extend `tests/test_text_blocks.py` if gaps
3. CLI command `tender-leads snapshot`:
   - `--url` (required), optional `--headed`, `-o` output path
   - Opens URL, calls `capture_snapshot(page)`, writes:
     - `main_text` (first 20k chars)
     - `listing_items` as JSON
     - `results_marker` line
   - Default path: `data/debug/snapshot-{timestamp}.txt` + `.json` sidecar
   - Russian log: «Снимок сохранён: …»
4. Sync `docs/platforms/sberbank-ast.md` with extraction-strategy (leaf fields, semantic actions)
5. Link snapshot command in README (debug section)

## Success criteria
- `pytest` passes offline (no network)
- `tender-leads snapshot --url https://www.sberbank-ast.ru/purchaseList.aspx` saves files when network OK; clear Russian error otherwise
- Grep `platforms/sberbank_ast.py` — no hardcoded CSS class selectors for data extraction

## Do not
- Period filter UI (task 12).
- LLM fallback (task 17).
- Re-add legacy web UI or deleted monolith code.
```
