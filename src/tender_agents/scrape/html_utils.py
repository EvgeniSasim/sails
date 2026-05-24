"""Извлечение контактов из HTML без LLM (бесплатно)."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from tender_agents.models import Contact

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(
    r"(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}"
    r"|\d{3}[\s\-]\d{3}[\s\-]\d{2}[\s\-]\d{2}"
)
INN_RE = re.compile(r"\bИНН[:\s]*(\d{10}|\d{12})\b", re.I)


def html_to_text_snippet(html: str, *, max_chars: int = 48_000) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    if len(text) > max_chars:
        return text[:max_chars] + "\n...[truncated]"
    return text


def extract_contacts_from_html(html: str) -> list[Contact]:
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True)
    contacts: list[Contact] = []
    seen: set[str] = set()

    for email in EMAIL_RE.findall(text):
        key = f"e:{email.lower()}"
        if key in seen:
            continue
        seen.add(key)
        contacts.append(Contact(email=email))

    for phone in PHONE_RE.findall(text):
        p = re.sub(r"\s+", " ", phone).strip()
        key = f"p:{p}"
        if key in seen:
            continue
        seen.add(key)
        contacts.append(Contact(phone=p))

    return contacts[:20]


def extract_inn_from_html(html: str) -> str | None:
    m = INN_RE.search(html)
    return m.group(1) if m else None


def first_heading_text(soup: BeautifulSoup, fallback: str = "") -> str:
    for tag in ("h1", "h2", "h3"):
        el = soup.find(tag)
        if el:
            t = el.get_text(strip=True)
            if len(t) > 5:
                return t
    return fallback
