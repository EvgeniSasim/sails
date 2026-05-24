# Jules Task: excel-import-contacts (можно Cursor, если Jules перегружен)

**Branch:** `feature/excel-import-contacts`

## Prompt (copy-paste)

```markdown
## Goal
Import contact profiles from Excel (.xlsx) / CSV with agent-assisted column mapping.

## UX
Settings → tab "Импорт" or Contacts toolbar:
1. Upload file (xlsx, csv; max 5MB)
2. Server parses first sheet → preview table (10 rows)
3. Agent (Yandex chat_json OR local heuristic) proposes mapping:
   - columns → full_name, organization, position, email, phone, event_title, event_date, notes
4. Manager confirms mapping in UI (dropdown per column)
5. Commit → upsert contact_profiles + optional ContactAppearance rows

## Implementation
- Dependency: `openpyxl` optional extra `pip install -e ".[excel]"` in pyproject.toml
- `src/tender_agents/excel_ingest/excel_import.py`:
  - `parse_workbook(bytes) -> list[dict[str, Any]]`
  - `suggest_mapping(headers, sample_rows) -> dict` using YandexStudioClient if configured else fuzzy match Russian headers (ФИО, компания, должность, email, телефон)
  - `apply_mapping(rows, mapping) -> list[ContactProfile]`
- Routes: POST `/contacts/import/upload`, POST `/contacts/import/commit`
- Store upload temp in `data/imports/` gitignored

## Events from Excel
If columns like "мероприятие", "доклад", "выставка" — create appearances with source_kind `import_excel`, appearance_type from column or default `event`.

## Success criteria
- Sample file with 3 columns (ФИО, Организация, Email) imports without manual mapping.
- Duplicate dedup_key merges, does not duplicate profiles.

## Do not
- Send full workbook to cloud without user consent — add checkbox "Использовать Yandex для сопоставления колонок" default off, heuristic first.
```
