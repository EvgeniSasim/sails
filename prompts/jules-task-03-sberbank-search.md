# Jules 03 — Sberbank-AST search v0

**Branch:** `jules/task01-03-sber-search`  
**Depends on:** merge 02

```markdown
You work on `tender_agents` with HumanSession available.

## Goal
Platform adapter skeleton + Sberbank-AST: open home, run search for one keyword, return listing URLs (no pagination, no detail yet).

## Read first
- docs/task-01-spec.md §6 (adapter contract)
- src/tender_agents/browser/session.py

## Implement
1. `src/tender_agents/platforms/base.py` — ABC `PlatformAdapter`:
   - `matches_url(url) -> bool`
   - `open_home(session)`
   - `search(session, keyword, filters) -> list[ListingItem]`
2. `ListingItem` in models.py: url, title (optional), preview (optional)
3. `src/tender_agents/platforms/registry.py` — resolve adapter by platform URL host
4. `docs/platforms/sberbank-ast.md` — document discovered search URL, selectors, notes (use Playwright trace/codegen mentally; pick stable selectors)
5. `src/tender_agents/platforms/sberbank_ast.py`:
   - matches `sberbank-ast.ru`
   - open_home → main page + cookies
   - search → fill search field, submit, parse result links from listing page
6. CLI subcommand or flag for smoke (choose one):
   - `tender-leads probe-search --platform-url ... -k "..."` OR extend `browse` with `--keyword`
   - prints Russian: «найдено ссылок: N» and first 3 URLs

## Success criteria
On a machine with network access to sberbank-ast.ru:
```
tender-leads probe-search --platform-url https://www.sberbank-ast.ru/ -k "закупка" -v
```
N > 0 links OR clear Russian error if site blocked (timeout with screenshot in data/debug/).

If Jules environment cannot reach site: implement selectors from public page structure and add `@pytest.mark.network` smoke test skipped by default.

## Do not
- Pagination or detail pages in this PR.
- Reintroduce deleted legacy adapters from old codebase.
```
