"""Извлечение структуры из текста страницы (без CSS-селекторов)."""

from __future__ import annotations

import re
from typing import Optional


def first_line_after(text: str, label: str) -> Optional[str]:
    idx = text.find(label)
    if idx < 0:
        return None
    rest = text[idx + len(label) :].lstrip(" :\t")
    for line in rest.splitlines():
        cleaned = line.strip()
        if cleaned:
            return cleaned
    return None


def parse_labeled_fields(text: str, labels: list[str]) -> dict[str, Optional[str]]:
    normalized = text.replace("\r", "")
    return {label: first_line_after(normalized, label) for label in labels}


def parse_tender_detail_text(text: str) -> dict[str, Optional[str]]:
    """Поля карточки тендера по текстовым меткам на странице."""
    normalized = text.replace("\r", "")
    external_id = None
    num_match = re.search(r"Сведения о закупке №\s*([^\s\n]+)", normalized)
    if num_match:
        external_id = num_match.group(1)

    publish_match = re.search(
        r"(\d{2}\.\d{2}\.\d{4})\s+\d{2}:\d{2}:\d{2}\s+Публикация извещения",
        normalized,
    )

    return {
        "external_id": external_id,
        "title": first_line_after(normalized, "Наименование объекта закупки"),
        "price": first_line_after(
            normalized,
            "Начальная (максимальная) цена контракта / Максимальное значение цены контракта",
        )
        or first_line_after(normalized, "Начальная (максимальная) цена контракта"),
        "customer_name": first_line_after(normalized, "Сведения об организаторе торгов"),
        "publish_date_str": publish_match.group(1) if publish_match else None,
        "deadline_str": first_line_after(
            normalized, "Дата и время окончания срока подачи заявок"
        ),
        "contacts": first_line_after(normalized, "Контактная информация"),
    }


def split_listing_blocks(text: str) -> list[str]:
    """Разбить выдачу на блоки по маркеру «№ <номер>»."""
    normalized = text.replace("\r", "")
    parts = re.split(r"(?=№\s*[\d-]+)", normalized)
    return [part.strip() for part in parts if part.strip() and re.search(r"№\s*[\d-]+", part)]


def extract_procedure_number(block: str) -> Optional[str]:
    match = re.search(r"№\s*([\d-]+)", block)
    return match.group(1) if match else None


def extract_purchase_urls(values: list[str]) -> list[str]:
    """Ссылки на карточки из значений hidden-полей или текста."""
    urls: list[str] = []
    seen: set[str] = set()
    pattern = re.compile(r"https?://[^\s\"']*purchaseview\.aspx\?id=\d+", re.I)
    for value in values:
        for match in pattern.findall(value):
            if match not in seen:
                seen.add(match)
                urls.append(match)
    return urls
