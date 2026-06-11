# Jules 14 — collect resilience

**Branch:** `jules/task02-14-resilience`  
**Depends on:** merge 13

```markdown
You work on HumanSession + orchestrator + page_context.

## Goal
Fewer silent failures; one retry on transient network; snapshot text saved when parse returns empty required fields.

## Read first
- src/tender_agents/browser/session.py
- src/tender_agents/collect/orchestrator.py
- docs/tasks/02-stability-smoke.md

## Implement
1. `HumanSession.goto`: one retry after 3s on timeout / `net::` errors (not on CaptchaRequiredError)
2. On detail parse with empty `title` AND empty `external_id`:
   - Save `data/debug/parse-fail-{timestamp}.txt` via `capture_main_text`
   - Russian WARNING with file path
3. On search failure after retry: include hint about RU network / VPN (reuse SiteUnreachableError message style)
4. Orchestrator: distinguish `skipped_filter` vs `skipped_duplicate` in stats (task 13 fields)
5. Update `docs/tasks/02-stability-smoke.md`:
   - snapshot command
   - `pytest -m "not network"`
   - server-side collect note (RU IP)
6. Add offline test for goto retry logic (mock page.goto fail once then ok)

## Success criteria
- `pytest` passes
- Smoke doc copy-paste commands valid
- Parse-fail snapshot created when adapter returns record with fallback title only and no external_id (test with mock)

## Do not
- Infinite retry loops.
- Captcha auto-solve.
```
