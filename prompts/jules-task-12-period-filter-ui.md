# Jules 12 — period filter in Sberbank UI

**Branch:** `jules/task02-12-period`  
**Depends on:** merge 11

```markdown
You work on SberbankAstAdapter + CollectFilters (date_from, date_to).

## Goal
When manager passes `--date-from` / `--date-to`, apply period in search UI on purchaseList.aspx before submit; keep detail-date fallback.

## Read first
- docs/task-01-spec.md §9 (no UI filter → filter on detail)
- docs/platforms/sberbank-ast.md
- src/tender_agents/platforms/base.py
- src/tender_agents/platforms/sberbank_ast.py

## Implement
1. Add optional method on `PlatformAdapter` (default no-op):
   ```python
   async def apply_period_filter(session, filters: CollectFilters) -> None: ...
   ```
2. In `SberbankAstAdapter.apply_period_filter`:
   - Open or ensure `purchaseList.aspx`
   - Find «дополнительные фильтры» / date inputs via semantic locators (label text, placeholder), not fragile ids
   - Set date_from / date_to when provided
   - Document discovered steps in `docs/platforms/sberbank-ast.md`
3. Call `apply_period_filter` from `search()` before filling keyword when any date set
4. Keep existing `open_detail` publish_date skip logic as fallback
5. Unit test: mock session verifies apply called when filters non-empty

## Success criteria
With network access:
```bash
tender-leads collect --platform-url https://www.sberbank-ast.ru/ \
  -k "crm" --date-from 2025-01-01 --max-per-keyword 3 --max-pages 1 -v
```
Russian log mentions период; saved tenders (if any) have publish_date ≥ date_from OR log explains UI filter applied.

If UI has no period fields: implement best-effort, document limitation, detail filter still works.

## Do not
- New storage backends.
- Zakupki adapter (task 16).
```
