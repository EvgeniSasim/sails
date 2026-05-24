"""Фильтрация мусора и проверка релевантности лидов."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from tender_agents.models import SearchResultItem

# Навигация / счётчики, не закупки
JUNK_TITLE_RE = re.compile(
    r"(?i)"
    r"(^Все\s*•|^В архиве\s*•|^Актуально\s*•)"
    r"|Подробная статистик"
    r"|Поиск по классификатор"
    r"|^Найти процедур"
    r"|^Закупки по (44|223)-ФЗ"
    r"|^Закупка по (44|223)-ФЗ"
    r"|^\s*АК\s+[«\"]"
    r"|^\s*АО\s+[«\"]"
    r"|^\s*ПАО\s+[«\"]"
    r"|•\s*[\d\s]{5,}"  # «Все • 2 404 005»
)

PROCEDURE_IN_TITLE = re.compile(
    r"(?i)(запрос\s+(цен|предложений)|процедура\s+закупки|конкурс|аукцион|"
    r"маркетингов|исследован|опрос|анкет|социолог|закупк|поставк|оказани)"
)

SURVEY_STEMS = (
    "опрос",
    "исследован",
    "анкет",
    "социолог",
    "маркетинг",
    "мнен",
    "респондент",
    "интервью",
)


def normalize_url(url: str) -> str:
    p = urlparse(url.strip())
    # убрать tracking-параметры
    drop = {"btid", "sqh", "utm_source", "utm_medium", "utm_campaign"}
    if p.query:
        q = {k: v for k, v in parse_qs(p.query, keep_blank_values=True).items() if k not in drop}
        query = urlencode(q, doseq=True)
    else:
        query = ""
    return urlunparse((p.scheme, p.netloc, p.path.rstrip("/"), "", query, ""))


def is_junk_title(title: str) -> bool:
    t = title.strip()
    if len(t) < 12:
        return True
    if JUNK_TITLE_RE.search(t):
        return True
    # только название компании без признаков процедуры
    if re.match(r"^(АО|АК|ПАО|ОАО|ООО)\s", t) and not PROCEDURE_IN_TITLE.search(t):
        return True
    return False


def is_relevant_to_keyword(title: str, keyword: str) -> bool:
    if is_junk_title(title):
        return False
    t = title.lower()
    k = keyword.lower().strip()
    if not k:
        return True

    # ключ связан с опросами/исследованиями — требуем совпадение в названии
    survey_key = any(s in k for s in SURVEY_STEMS)
    if not survey_key:
        return True

    # слова из ключа (≥ 5 символов)
    stems = [w for w in re.split(r"[\s\-–—,]+", k) if len(w) >= 5]
    if any(s in t for s in stems):
        return True

    # доменные термины, если они есть в ключе
    for stem in SURVEY_STEMS:
        if stem in k and stem in t:
            return True

    # zakupki: «маркетинговоеисследование» слитно
    if "маркетинг" in k and "исследован" in t:
        return True
    if "социолог" in k and "социолог" in t:
        return True
    if "опрос" in k and "опрос" in t:
        return True
    if "анкет" in k and "анкет" in t:
        return True

    return False


def filter_search_items(
    items: list[SearchResultItem],
    *,
    keyword: str,
    source_id: str,
) -> list[SearchResultItem]:
    out: list[SearchResultItem] = []
    for item in items:
        if not is_relevant_to_keyword(item.title, keyword):
            continue
        # B2B/Sber: только ссылки на процедуры
        if source_id in ("b2b_center", "sberbank_ast"):
            href = item.url.lower()
            if source_id == "b2b_center":
                ok = (
                    "tender-" in href
                    or re.search(r"/market/[^/]+/tender-\d+", href)
                    or ("/market/" in href and "запрос" in item.title.lower())
                )
                if not ok:
                    continue
            if source_id == "sberbank_ast" and not re.search(
                r"(purchase|procedure|notice|trade|lot|view)", href
            ):
                continue
        out.append(item)
    return out
