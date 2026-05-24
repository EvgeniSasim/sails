# Jules Task: research-captcha-compliance

**Branch:** `jules/research-captcha-compliance`

## Prompt (copy-paste в Jules)

```markdown
## Goal
Design and implement infrastructure for contact web research that survives captcha/blocking and documents compliance (Russia 152-FZ oriented, open sources only).

## Context
`contact_research_agent.py` fetches Yandex/DDG/Brave and pages. Often: captcha, 404, rate limits. Sales managers may solve captcha manually or use a third-party solving service via env vars.

## Implement (minimal but complete)

### 1. Research job queue (SQLite tables or reuse schema_meta pattern)
- `contact_research_jobs`: id, profile_id, status (pending|running|needs_captcha|needs_manual|completed|failed), query, created_at, error, result_json
- Status `needs_captcha` stores: search_engine, challenge_url or screenshot path, instructions for manager

### 2. Pluggable fetch layer `src/tender_agents/research/fetchers.py`
- `HttpxFetcher` (default)
- `ManualCaptchaFetcher` — pauses job, exposes URL for manager to open in browser; resume endpoint accepts cookies header or pasted HTML file upload
- `ExternalCaptchaFetcher` — optional stub reading env `CAPTCHA_SERVICE_URL` + `CAPTCHA_API_KEY` (no hardcoded vendor); document in .env.example only

### 3. API routes (FastAPI in web/app.py)
- POST `/contact/{id}/research` → creates job, returns job_id (async background)
- GET `/contact/{id}/research/status` — poll status
- POST `/contact/research/{job_id}/resume` — form: html_file OR cookies_text for manual continue
- GET `/research/jobs` — list jobs needing captcha (for manager dashboard widget)

### 4. Compliance module `src/tender_agents/compliance.py`
- `record_provenance(profile_id, source_url, field, value, collected_at)` → append-only log table `data_provenance_log`
- `is_allowed_source_url(url)` — block obviously wrong domains; allow public web
- README section `docs/compliance-152fz.md` (NOT legal advice): open sources only, purpose B2B sales, minimization, retention 24mo suggestion, manager verification flag `channel_verified_at` on contact_profiles (migration column)

### 5. Update contact research agent
- Use fetcher chain: httpx → on captcha marker set job needs_captcha, do not write junk emails
- Never store emails failing `is_plausible_contact_email`

## UI (minimal HTML in html_pages.py)
- On contact card: if job needs_captcha — show link "Открыть страницу" + form upload HTML / "Я прошёл капчу — продолжить"
- Banner: "Данные только из открытых источников; перед КП подтвердите канал"

## Tests
- Unit tests for captcha detection heuristics (HTML contains showcaptcha, checkbox-captcha)
- Unit test provenance log write

## Success criteria
- Research no longer silently returns 0 results without explaining captcha.
- Manager can resume after manual step.
- Provenance log row per email/phone saved from page.

## Do not
- Implement full 2captcha integration unless env configured — stub interface is enough.
- Scrape login-walled social networks automatically.
```

## Notes for reviewer

Юрист должен утвердить `docs/compliance-152fz.md` до продакшена.
