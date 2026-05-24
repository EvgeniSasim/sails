# Jules Task: zakupki-resilience

**Repo:** tender-lead-agents (agents)  
**Branch:** `jules/zakupki-resilience`  
**Owner:** Jules → human review PR

## Prompt (copy-paste в Jules)

```markdown
You are working on the Python package `tender_lead_agents` in this repository.

## Goal
Make zakupki.gov.ru tender enrichment reliable for production sales use.

## Problems to fix
1. printForm/view.html URLs often return HTTP 404 — search results must prefer common-info.html and enrich must try multiple URL candidates before failing.
2. When all URLs fail, save a degraded lead (title, customer from search) instead of crashing the whole EnrichAgent loop.
3. Optional: respect configurable delay between requests (settings.request_delay_sec) and retry with backoff on 429/503.

## Files to read first
- src/tender_agents/scrape/parsers/zakupki.py
- src/tender_agents/sources/zakupki.py
- src/tender_agents/agents/enrich_agent.py
- tests/ if any; add minimal tests for `detail_url_candidates()` and `normalize_detail_url()` without network

## Requirements
- Do not break existing search() behavior.
- Keep httpx-only (no new paid deps).
- Add or extend unit tests for URL candidate generation (use a fixture URL with purchaseNoticeNumber).
- Log clearly when fallback URL used vs degraded save.

## Success criteria
- `detail_url_candidates(printForm_url)` includes common-info variant with regNumber.
- enrich_detail does not raise on 404 for printForm-only URLs.
- EnrichAgent continues processing next items after single failure.

## Do not
- Change unrelated B2B/Sberbank adapters.
- Commit secrets or .env.
```

## After merge (Cursor/human)

- Run `tender-leads run -s zakupki -k "crm" --max-per-keyword 3` on server or locally.
- Verify dashboard shows new/updated leads.
