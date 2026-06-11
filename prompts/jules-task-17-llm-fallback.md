# Jules 17 — LLM extract fallback (optional)

**Branch:** `jules/task02-17-llm`  
**Depends on:** merge 16

```markdown
You work on page_context snapshots and TenderRecord parsing.

## Goal
When leaf + text parsing miss required fields, optional Yandex GPT extracts structured fields from compressed page text.

## Read first
- docs/platforms/extraction-strategy.md (level 4)
- src/tender_agents/browser/page_context.py (`PageSnapshot`)
- src/tender_agents/models.py

## Implement
1. Optional extra: `llm = ["httpx>=0.27"]` if not already; settings via env:
   - `YANDEX_API_KEY`, `YANDEX_FOLDER_ID`, `YANDEX_MODEL` (document in README, never commit secrets)
   - `YANDEX_USE_RESPONSES_API=false` — chat/completions only
2. `src/tender_agents/extract/llm_fallback.py`:
   - `async def extract_tender_from_text(text: str, url: str) -> dict`
   - Prompt: Russian instructions, return JSON only with keys matching TenderRecord optional fields
   - Truncate input to ~12k chars (main content)
3. `SberbankAstAdapter.open_detail`:
   - After `parse_tender_detail_text`, if missing `title` or `external_id` AND `plan.use_llm_fallback` / env `TENDER_LEADS_LLM_FALLBACK=1`:
   - Call llm_fallback, merge non-empty fields
4. CLI: `--llm-fallback` on `collect` and `probe-search --fetch-details`
   - Without API key: Russian warning, continue without LLM
5. Offline test: mock HTTP response → parsed dict merged into record
6. Document cost/latency warning in README (not for every lot by default)

## Success criteria
- Default collect unchanged when flag off
- With flag + mock API in test: broken fixture text still yields title + external_id
- No API keys in repo

## Do not
- Make LLM mandatory for collect.
- Reintroduce full old yandex agent orchestrator from deleted monolith.
```
