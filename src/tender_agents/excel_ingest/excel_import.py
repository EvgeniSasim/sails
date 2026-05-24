from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timezone
from typing import Any

from tender_agents.models import ContactAppearance, ContactProfile

logger = logging.getLogger(__name__)

MAPPING_FIELDS = {
    "full_name": ["фио", "имя", "фамилия", "fio", "name", "full name", "full_name"],
    "organization": ["организация", "компания", "company", "organization", "org"],
    "position": ["должность", "position", "role", "job title"],
    "email": ["email", "e-mail", "почта"],
    "phone": ["телефон", "phone", "тел", "mobile"],
    "event_title": ["мероприятие", "доклад", "выставка", "event", "title", "conference"],
    "event_date": ["дата", "date"],
    "notes": ["заметки", "notes", "комментарий", "примечание"],
}


def parse_workbook(content: bytes, filename: str) -> list[dict[str, Any]]:
    """Парсит xlsx или csv и возвращает список словарей."""
    low = (filename or "").lower()
    if low.endswith(".csv"):
        text = content.decode("utf-8-sig", errors="replace")
        f = io.StringIO(text)
        try:
            dialect = csv.Sniffer().sniff(text[:2000])
        except Exception:
            dialect = "excel"
        reader = csv.DictReader(f, dialect=dialect)
        return [dict(row) for row in reader]

    try:
        import openpyxl
    except ImportError as e:
        raise ImportError("Установите: pip install -e '.[excel]'") from e

    wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
    sheet = wb.active
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return []

    headers = [str(h).strip() if h is not None else f"col_{i}" for i, h in enumerate(rows[0])]
    result: list[dict[str, Any]] = []
    for row in rows[1:]:
        if any(row):
            result.append(dict(zip(headers, row)))
    return result


async def suggest_mapping(
    headers: list[str], sample_rows: list[dict], use_yandex: bool = False
) -> dict[str, str]:
    """Предлагает маппинг колонок (эвристика; Yandex — только по явному флагу)."""
    if use_yandex:
        try:
            from tender_agents.yandex.client import YandexStudioClient

            client = YandexStudioClient()
            instructions = (
                "Сопоставь заголовки Excel с полями: full_name, organization, position, email, "
                "phone, event_title, event_date, notes. JSON: ключ — поле, значение — заголовок из файла."
            )
            user_input = f"Заголовки: {headers}\nПримеры: {sample_rows[:3]}"
            res = await client.chat_json(instructions=instructions, user_input=user_input)
            valid = {k: v for k, v in res.items() if k in MAPPING_FIELDS and v in headers}
            if valid:
                return valid
        except Exception as e:
            logger.warning("Yandex suggest_mapping failed: %s", e)

    mapping: dict[str, str] = {}
    for field, keywords in MAPPING_FIELDS.items():
        for h in headers:
            h_lower = h.lower()
            if any(k in h_lower for k in keywords):
                mapping[field] = h
                break
    return mapping


def apply_mapping(
    rows: list[dict], mapping: dict[str, str]
) -> tuple[list[ContactProfile], list[ContactAppearance]]:
    profiles: list[ContactProfile] = []
    appearances: list[ContactAppearance] = []
    now = datetime.now(timezone.utc)

    for row in rows:
        name = str(row.get(mapping.get("full_name", ""), "") or "").strip()
        if not name:
            continue
        org = str(row.get(mapping.get("organization", ""), "") or "").strip() or "—"

        profile = ContactProfile(
            organization=org,
            full_name=name,
            position=str(row.get(mapping.get("position", ""), "") or "").strip() or None,
            email=str(row.get(mapping.get("email", ""), "") or "").strip() or None,
            phone=str(row.get(mapping.get("phone", ""), "") or "").strip() or None,
            notes=str(row.get(mapping.get("notes", ""), "") or "").strip() or None,
            first_seen_at=now,
            last_seen_at=now,
        )
        idx = len(profiles)
        profiles.append(profile)

        event_title = str(row.get(mapping.get("event_title", ""), "") or "").strip()
        if event_title:
            from tender_agents.contacts_db import _parse_pub_date

            raw_date = row.get(mapping.get("event_date", ""))
            appeared_at = now
            if isinstance(raw_date, datetime):
                appeared_at = raw_date
            elif isinstance(raw_date, str) and raw_date.strip():
                parsed = _parse_pub_date(raw_date)
                if parsed:
                    appeared_at = parsed

            appearances.append(
                ContactAppearance(
                    profile_id=idx,
                    source_kind="import_excel",
                    source_title=event_title,
                    source_url="internal://import",
                    appeared_at=appeared_at,
                    appearance_type="event",
                )
            )
            profile.first_seen_at = appeared_at
            profile.last_seen_at = appeared_at

    return profiles, appearances
