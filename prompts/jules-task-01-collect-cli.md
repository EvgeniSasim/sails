# Jules 01 — CLI `collect`

**Branch:** `jules/task01-01-collect-cli`  
**Spec:** `docs/task-01-spec.md` §7 step 1

```markdown
You work on Python package `tender_agents` (repo reset v0.2.0 — minimal skeleton only).

## Goal
Add `tender-leads collect` CLI command: parse manager inputs and print a clear collection plan (no browser yet).

## Read first
- docs/task-01-spec.md (sections 4 and 7 step 1)
- src/tender_agents/cli.py
- pyproject.toml

## Implement
1. `src/tender_agents/models.py` with pydantic models:
   - `CollectFilters` (date_from, date_to optional)
   - `CollectPlan` (platform_url, keywords, filters, max_per_keyword, max_pages)
2. Extend `pyproject.toml` dependencies: `pydantic>=2.7`
3. Typer command `collect` with options:
   - `--platform-url` (required, http/https, non-empty host)
   - `-k` / `--keyword` repeatable (at least one)
   - `--date-from`, `--date-to` (YYYY-MM-DD)
   - `--max-per-keyword` (default 10)
   - `--max-pages` (default 5)
   - `-v` / `--verbose`
4. Validate dates; if only date_from set, OK.
5. Print Russian summary to console (Rich): platform host, keywords, period, limits.
6. Exit code 0. Do NOT start Playwright yet.

## Success criteria
```bash
pip install -e .
tender-leads collect --platform-url https://www.sberbank-ast.ru/ -k "crm" --date-from 2026-05-01 -v
```
prints a meaningful plan in Russian and exits 0.

Invalid URL → typer error, non-zero exit.

## Do not
- Add web UI, FastAPI, or old deleted modules.
- Commit secrets or .env.
- Implement browser or platform adapters in this PR.
```
