# Cursor Task: manager-facing features (не Jules)

**Branch:** `feature/manager-queue-and-filters`

## Prompt (copy-paste в Cursor)

```markdown
## Goal
Ship manager-visible features in existing FastAPI dashboard (Russian UI).

## P0 — Tenders by period
- Extend `LeadFilters` in db.py: `date_from`, `date_to` (filter on publish_date parsed or created_at ISO).
- Dashboard `/` form: date inputs or presets (7д / 30д / квартал).
- Show count in hint.

## P0 — Contact profile structure
Extend contact_profiles (migration in contacts_db.py):
- `bio` TEXT — описание профиля (редактируемое в UI)
- Use existing `contact_appearances` with typed `appearance_type`:
  - `conference`, `exhibition`, `talk`, `interview`, `rating`, `article`, `web_*`
- UI contact_detail_page:
  - Section "Описание" (textarea POST save)
  - Section "Мероприятия и выступления" — table: дата | тип | название | место | ссылка
  - Form "Добавить мероприятие" manually

## P1 — Manager queue (simplified)
New route `/queue` or enhance `/`:
- Tabs: Горячие тендеры | ЛПР | Связанные
- Filter `ready_for_outreach`: has verified email OR hot tender link confirmed

## P1 — Channel verification
- `channel_verified_at` on contact_profiles
- Button "Канал проверен" on contact card

Read: contacts_db.py, html_pages.py, app.py, models.py

## Success criteria
- Manager can filter tenders published in last 30 days.
- Manager can add bio + manual event on contact without Excel.

## Do not
- Implement Excel import here (separate PR).
```
