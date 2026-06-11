# Jules 02 — HumanSession + `browse`

**Branch:** `jules/task01-02-browser`  
**Depends on:** merge 01

```markdown
You work on `tender_agents` after task01-01-collect-cli is merged.

## Goal
Playwright-based human-like browser session + `tender-leads browse` for smoke testing (open site, accept cookies).

## Read first
- docs/task-01-spec.md §5 (HumanSession rules)
- src/tender_agents/cli.py
- pyproject.toml optional `[browser]`

## Implement
1. `src/tender_agents/browser/__init__.py`
2. `src/tender_agents/browser/cookies.py` — `accept_cookies(page)` tries common Russian/EN consent buttons (Принять, Согласен, Accept, etc.)
3. `src/tender_agents/browser/session.py` — `HumanSession` async context manager:
   - Chromium, viewport 1920x1080, locale ru-RU
   - `goto(url)`, `human_delay()` random 0.8–2.5s
   - `accept_cookies()` after navigation
   - on failure: save screenshot to `data/debug/` with timestamp
   - `--headed` support via constructor flag
4. CLI command `browse`:
   - `--url` required
   - `--headed` flag
   - logs Russian: «Открываю…», «Cookie приняты» or «баннер не найден», «Готово»
5. Ensure `data/debug/` is gitignored (update .gitignore if needed).
6. README snippet: `pip install -e ".[browser]"` and `playwright install chromium`

## Success criteria
```bash
pip install -e ".[browser]"
playwright install chromium
tender-leads browse --url https://www.sberbank-ast.ru/ --headed
```
opens browser, attempts cookie consent, exits 0 with Russian log lines.

Unit test optional: mock page for cookie button matching (no network).

## Do not
- Implement Sberbank search or collect orchestration yet.
- Commit secrets.
```
