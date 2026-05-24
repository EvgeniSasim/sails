"""Excel/CSV contact import with heuristic column mapping."""

from __future__ import annotations

import csv
import io
import re
from typing import Any

from tender_agents.contacts_db import ContactRepository
from tender_agents.models import ContactProfile

HEADER_MAP: dict[str, str] = {
    "фио": "full_name",
    "ф.и.о": "full_name",
    "имя": "full_name",
    "full_name": "full_name",
    "name": "full_name",
    "компания": "organization",
    "организация": "organization",
    "organization": "organization",
    "company": "organization",
    "должность": "position",
    "position": "position",
    "email": "email",
    "e-mail": "email",
    "почта": "email",
    "телефон": "phone",
    "phone": "phone",
    "мероприятие": "event_title",
    "доклад": "event_title",
    "выставка": "event_title",
    "event": "event_title",
    "дата": "event_date",
    "заметки": "notes",
    "notes": "notes",
}


def parse_workbook(data: bytes, *, filename: str = "") -> tuple[list[str], list[dict[str, Any]]]:
    low = (filename or "").lower()
    if low.endswith(".csv") or (not low.endswith((".xlsx", ".xls")) and b"," in data[:2000]):
        text = data.decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        headers = list(reader.fieldnames or [])
        rows = [dict(r) for r in reader]
        return headers, rows

    try:
        import openpyxl
    except ImportError as e:
        raise RuntimeError("Установите openpyxl: pip install -e '.[excel]'") from e

    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    sheet = wb.active
    rows_iter = sheet.iter_rows(values_only=True)
    try:
        header_row = next(rows_iter)
    except StopIteration:
        return [], []
    headers = [str(c or "").strip() for c in header_row]
    rows: list[dict[str, Any]] = []
    for row in rows_iter:
        if not any(row):
            continue
        rows.append({headers[i]: row[i] for i in range(min(len(headers), len(row))) if headers[i]})
    return headers, rows


def suggest_mapping(headers: list[str], sample_rows: list[dict[str, Any]]) -> dict[str, str | None]:
    mapping: dict[str, str | None] = {}
    for h in headers:
        key = re.sub(r"\s+", " ", (h or "").strip().lower())
        mapping[h] = HEADER_MAP.get(key)
        if mapping[h]:
            continue
        for token, field in HEADER_MAP.items():
            if token in key:
                mapping[h] = field
                break
        else:
            mapping[h] = None
    if not any(v == "full_name" for v in mapping.values()) and headers:
        mapping[headers[0]] = "full_name"
    if len(headers) > 1 and not any(v == "organization" for v in mapping.values()):
        mapping[headers[1]] = "organization"
    return mapping


async def apply_mapping(
    cr: ContactRepository,
    rows: list[dict[str, Any]],
    mapping: dict[str, str | None],
    *,
    create_events: bool = True,
) -> dict[str, int]:
    imported = 0
    merged = 0
    events = 0
    for raw in rows:
        data: dict[str, Any] = {}
        for col, field in mapping.items():
            if not field or col not in raw:
                continue
            val = raw.get(col)
            if val is None or str(val).strip() == "":
                continue
            data[field] = str(val).strip()
        name = data.get("full_name") or ""
        org = data.get("organization") or ""
        if not name.strip():
            continue
        profile = ContactProfile(
            organization=org or "—",
            full_name=name.strip(),
            position=data.get("position"),
            email=data.get("email"),
            phone=data.get("phone"),
            notes=data.get("notes"),
        )
        pid, is_new = await cr.upsert_profile(profile)
        if is_new:
            imported += 1
        else:
            merged += 1
        if create_events and pid and data.get("event_title"):
            await cr.add_manual_appearance(
                pid,
                appearance_type="event",
                source_title=data["event_title"],
                snippet=data.get("event_date"),
            )
            events += 1
    return {"imported": imported, "merged": merged, "events": events}
