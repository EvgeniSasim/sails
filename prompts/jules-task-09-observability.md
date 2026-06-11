# Jules 09 — observability + README

**Branch:** `jules/task01-09-observability`  
**Depends on:** merge 08

```markdown
You work on complete task-01 collect pipeline.

## Goal
Production-ready logging, error screenshots, README for managers; polish AGENTS.md.

## Read first
- docs/task-01-spec.md step 9
- README.md, AGENTS.md

## Implement
1. Logging config in CLI when `-v`: format with time, level, Russian step messages
2. On adapter errors: screenshot to data/debug/, continue next item where possible
3. Captcha/login wall detection: log «Нужен ручной ввод» and stop gracefully (no infinite retry)
4. README.md (Russian):
   - install `.[browser]`, playwright install
   - full collect example for sberbank-ast.ru
   - explain data/collect and tender-leads list
   - polite rate limits (one browser, delays)
5. Link to docs/task-01-spec.md and docs/jules-sessions.md
6. Minimal pytest: models validation, store dedupe, registry.matches_url (no network)

## Success criteria
- `pytest` passes offline tests
- README commands copy-paste valid
- Manager can understand failure from log + screenshot path alone

## Do not
- Re-add old CRM UI or settings tabs.
```
