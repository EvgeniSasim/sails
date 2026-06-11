# Jules 16 — Zakupki adapter v0 (httpx)

**Branch:** `jules/task02-16-zakupki`  
**Depends on:** merge 15

```markdown
You work on PlatformAdapter registry and collect pipeline.

## Goal
Second platform: zakupki.gov.ru (EIS public search) via httpx — no Playwright required for this adapter.

## Read first
- docs/task-01-spec.md §6 (adapter contract)
- src/tender_agents/platforms/sberbank_ast.py (reference)
- src/tender_agents/platforms/registry.py

## Implement
1. Optional dependency group in pyproject.toml: `httpx = ["httpx>=0.27"]` or add httpx to main deps if lightweight
2. `src/tender_agents/platforms/zakupki.py`:
   - `matches_url`: zakupki.gov.ru host
   - Uses httpx.AsyncClient with reasonable timeout and User-Agent
   - `open_home` / `search` / `iter_listing_pages` / `open_detail` implemented:
     - Search: public EPZ search or documented HTML endpoint (no paid API)
     - Return ListingItem + TenderRecord same fields as spec §4
   - If site blocks datacenter IP: raise clear Russian error
3. Register in `platforms/__init__.py`
4. `docs/platforms/zakupki.md` — URLs, limits, no-login note
5. Orchestrator: if adapter does not need browser, skip HumanSession or use httpx-only path:
   - Prefer: adapter flag `needs_browser: bool = True` on base class; Zakupki returns False
   - `run_collect` opens browser only when any adapter needs it OR single-adapter check
6. Offline tests with saved HTML fixture for search results page (like task 11)

## Success criteria
```bash
pip install -e ".[httpx]"   # or equivalent
tender-leads probe-search --platform-url https://zakupki.gov.ru -k "crm" --max-per-keyword 3
```
prints ≥1 link from fixture test offline; live network optional `@pytest.mark.network`

## Do not
- Playwright for zakupki in this PR (httpx only).
- Login / paid EIS API.
- B2B-center, gosplan adapters.
```
