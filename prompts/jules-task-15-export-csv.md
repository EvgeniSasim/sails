# Jules 15 — export CSV for managers

**Branch:** `jules/task02-15-export`  
**Depends on:** merge 14

```markdown
You work on SQLite tenders store and CLI.

## Goal
Manager exports last N tenders to CSV without SQL.

## Read first
- src/tender_agents/collect/db.py
- src/tender_agents/cli.py (`list` command)
- src/tender_agents/models.py (`TenderRecord`)

## Implement
1. CLI `tender-leads export`:
   - `--last N` (default 100)
   - `--format csv` (only csv in this PR; leave hook for json)
   - `--output path.csv` optional; default `data/export/tenders-{date}.csv`
   - `--platform` optional filter by platform host
2. CSV columns (UTF-8 with BOM for Excel):
   external_id, title, customer_name, price, publish_date, deadline, url, matched_keyword, collected_at
3. CLI `tender-leads show`:
   - `--id EXTERNAL_ID` or `--url URL`
   - Prints one tender as Rich panel (all fields, Russian labels)
4. README section «Экспорт для Excel»

## Success criteria
```bash
tender-leads export --last 50 --output /tmp/tenders.csv
tender-leads show --id 0376100002725000010
```
works after prior collect; empty DB → polite Russian message, exit 0

## Do not
- Web UI.
- Email sending.
```
