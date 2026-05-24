"""Нормализация текста для отображения."""

from __future__ import annotations

import re

# «маркетинговоеисследование» → «маркетинговое исследование»
WORD_SPLITS = [
    (r"маркетинговоеисследование", "маркетинговое исследование"),
    (r"социологическоеисследование", "социологическое исследование"),
    (r"проведениюсоциолог", "проведению социолог"),
    (r"проведениюонлайн", "проведению онлайн"),
    (r"организацииипроведению", "организации и проведению"),
    (r"общественногомнения", "общественного мнения"),
]


def normalize_title(title: str) -> str:
    t = re.sub(r"\s+", " ", title or "").strip()
    for pattern, repl in WORD_SPLITS:
        t = re.sub(pattern, repl, t, flags=re.I)
    return t


_ORG_PREFIXES = (
    r"^ооо\s+",
    r"^оао\s+",
    r"^ао\s+",
    r"^пао\s+",
    r"^зао\s+",
    r"^нао\s+",
    r"^фгуп\s+",
    r"^акционерное общество\s+",
    r"^публичное акционерное общество\s+",
)


def normalize_org_name(name: str) -> str:
    """Нормализация названия компании для сопоставления с заказчиком в тендере."""
    s = re.sub(r"\s+", " ", (name or "").lower().strip())
    for p in _ORG_PREFIXES:
        s = re.sub(p, "", s, flags=re.I)
    s = s.replace("«", "").replace("»", "").replace('"', "'")
    return s.strip()


def org_token_jaccard(a: str, b: str) -> float:
    ta = {t for t in normalize_org_name(a).split() if len(t) > 2}
    tb = {t for t in normalize_org_name(b).split() if len(t) > 2}
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb) or 1
    return inter / union


# Домены поисковиков, CDN, заглушек — не контакты людей
_JUNK_EMAIL_DOMAINS = (
    "duckduckgo.com",
    "ddg.co",
    "google.com",
    "googlemail.com",
    "gstatic.com",
    "yandex.ru",
    "yandex.net",
    "ya.ru",
    "bing.com",
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "linkedin.com",
    "w3.org",
    "schema.org",
    "sentry.io",
    "example.com",
    "localhost",
)

_JUNK_EMAIL_LOCAL = (
    "error",
    "error-lite",
    "noreply",
    "no-reply",
    "donotreply",
    "support",
    "help",
    "feedback",
    "mailer-daemon",
    "postmaster",
)


def is_plausible_contact_email(email: str) -> bool:
    e = (email or "").strip().lower()
    if not e or "@" not in e:
        return False
    local, _, domain = e.partition("@")
    if not local or not domain or "." not in domain:
        return False
    if any(domain == d or domain.endswith("." + d) for d in _JUNK_EMAIL_DOMAINS):
        return False
    if any(local.startswith(p) or p in local for p in _JUNK_EMAIL_LOCAL):
        return False
    if len(local) < 2 or len(domain) < 4:
        return False
    return True


_CYR_LAT = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


def org_latin_slug(organization: str) -> str | None:
    """Транслит бренда для домена: Нанолек → nanolek."""
    n = normalize_org_name(organization)
    if not n:
        return None
    out: list[str] = []
    for ch in n:
        if ch in _CYR_LAT:
            out.append(_CYR_LAT[ch])
        elif ch.isascii() and ch.isalnum():
            out.append(ch)
    slug = "".join(out).replace(" ", "")
    return slug if len(slug) >= 3 else None


def person_name_tokens(full_name: str) -> list[str]:
    """Значимые части ФИО для поиска в тексте."""
    stop = {"и", "в", "на", "the", "of"}
    return [
        t.lower()
        for t in re.split(r"[\s\-]+", full_name or "")
        if len(t) > 2 and t.lower() not in stop
    ]


def name_likely_in_text(full_name: str, text: str, *, min_hits: int | None = None) -> bool:
    """Есть ли в тексте достаточно частей ФИО."""
    tokens = person_name_tokens(full_name)
    if not tokens:
        return False
    low = (text or "").lower()
    hits = sum(1 for t in tokens if t in low)
    need = min_hits if min_hits is not None else (2 if len(tokens) >= 2 else 1)
    return hits >= min(need, len(tokens))


def is_plausible_contact_phone(phone: str) -> bool:
    raw = (phone or "").strip()
    if not raw:
        return False
    # Склейки вида 789337893-67 из HTML/JS
    if re.search(r"\d{7,}-\d{1,4}$", raw):
        return False
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    if not digits.startswith("7") or len(digits) != 11:
        return False
    # Из открытой выдачи почти всегда мобильный; 893… без +7 — мусор
    if digits[1] != "9":
        return False
    return True
