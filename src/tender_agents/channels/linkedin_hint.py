"""Публичные подсказки для обогащения контакта (без парсинга закрытых соцсетей)."""

from __future__ import annotations

from urllib.parse import quote


def linkedin_people_search_url(name: str, company: str) -> str:
    """Поиск людей в LinkedIn по ФИО + компания (ручной клик из CRM)."""
    q = f"{name.strip()} {company.strip()}".strip()
    return "https://www.linkedin.com/search/results/people/?keywords=" + quote(q)


def yandex_people_search_url(name: str, company: str) -> str:
    """Открытая выдача Яндекса — часто есть страница компании / пресс-подразделение."""
    q = f"{name.strip()} {company.strip()} контакт email".strip()
    return "https://yandex.ru/search/?text=" + quote(q)
