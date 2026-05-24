# AGENTS.md — tender-lead-agents

## Product

B2B sales tool for **FeedBackTalk** (CX / surveys / HR pulse). Managers get tender leads and executive contacts (HR, CX, research buyers).

## Stack

- Python 3.11+, package `src/tender_agents`
- CLI: `tender-leads` (typer)
- Web: FastAPI + HTML in `src/tender_agents/web/`
- DB: SQLite async (SQLAlchemy), `data/leads.db`
- Config: `config/*.yaml`, secrets in `.env` (never commit)

## Layout

| Path | Role |
|------|------|
| `src/tender_agents/agents/` | Search, Enrich, Store, contact_research |
| `src/tender_agents/scrape/parsers/zakupki.py` | Free EIS parser (httpx) |
| `src/tender_agents/contacts_db.py` | Contact profiles + appearances |
| `src/tender_agents/db.py` | Tender leads |
| `prompts/` | Prompt specs for Jules / Cursor tasks |
| `docs/` | Product and deploy docs |

## Conventions

- Russian UI strings in `html_pages.py`
- Minimal diffs; match existing style
- No secrets in code; use `settings.py` / pydantic-settings
- Yandex LLM: `chat/completions` only (`YANDEX_USE_RESPONSES_API=false`)

## Run

```bash
pip install -e ".[web]"
tender-leads serve
tender-leads run -s zakupki -k "crm" --max-per-keyword 5
```

## Jules task prompts

See `prompts/jules-task-*.md` and `docs/product-roadmap-v2.md`.
