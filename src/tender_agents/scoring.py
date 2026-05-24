"""Скоринг лидов для продаж FeedBackTalk."""

from __future__ import annotations

import re
from datetime import datetime

from tender_agents.models import LeadSegment, TenderLead, TenderStatus
from tender_agents.text_utils import normalize_title

NEGATIVE_RE = re.compile(
    r"(?i)(поставк[аи]\s+книг|периферийн|медицинск|бумаг[аи]|мебел|"
    r"канцеляр|автомобил|топлив|продукт[аы]\s+питани)"
)

HR_RE = re.compile(
    r"(?i)(сотрудник|персонал|hr|кадр|вовлечённост|вовлеченност|"
    r"360|оценк[аи]\s+персонал|климат|eNPS|пульс.?опрос|hr-)"
)

CX_RE = re.compile(
    r"(?i)(клиентск|обратн[а-я]*\s+связ|NPS|CSAT|CES|лояльност|"
    r"удовлетворённост|удовлетворенност|клиентск[а-я]*\s+опыт|CX|VOC)"
)

RESEARCH_RE = re.compile(
    r"(?i)(маркетингов|социолог|исследован|анкетир|респондент|фокус.?групп)"
)

GOV_RE = re.compile(
    r"(?i)(государств|муниципал|федеральн|бюджетн|казённ|казенн|"
    r"министерств|департамент|администрац|государственн)"
)

PLATFORM_RE = re.compile(
    r"(?i)(платформ[аы]\s+опрос|систем[аы]\s+.*опрос|электронн.*опрос|"
    r"онлайн.?опрос|проведени.*опрос)"
)


def detect_segment(title: str, description: str = "") -> LeadSegment:
    text = f"{title} {description}"
    if HR_RE.search(text):
        return LeadSegment.HR
    if CX_RE.search(text):
        return LeadSegment.CX
    if RESEARCH_RE.search(text):
        return LeadSegment.RESEARCH
    if GOV_RE.search(text) and RESEARCH_RE.search(text):
        return LeadSegment.GOV
    if GOV_RE.search(text):
        return LeadSegment.GOV
    if PLATFORM_RE.search(text):
        return LeadSegment.CX
    return LeadSegment.OTHER


def score_lead(lead: TenderLead) -> tuple[int, LeadSegment, list[str]]:
    title = normalize_title(lead.title)
    desc = lead.description_snippet or ""
    text = f"{title} {desc}".lower()
    segment = detect_segment(title, desc)
    roles_blob = " ".join((c.role or "") for c in lead.contacts).lower()
    if lead.channel == "open_media":
        if segment == LeadSegment.OTHER and (
            HR_RE.search(roles_blob)
            or HR_RE.search(lead.context_title or "")
            or "персонал" in (lead.context_title or "").lower()
        ):
            segment = LeadSegment.HR

    reasons: list[str] = []
    score = 0

    if NEGATIVE_RE.search(text) and lead.channel != "open_media":
        score -= 50
        reasons.append("нецелевой предмет закупки")

    if lead.channel == "open_media":
        score += 25
        reasons.append("открытый канал (СМИ / рейтинг / подборка)")
        if any(
            (c.linkedin_search_url or c.yandex_search_url or c.email or c.phone)
            for c in lead.contacts
        ):
            score += 10
            reasons.append("есть зацепки для контакта (поиск / email / тел.)")

    if RESEARCH_RE.search(text):
        score += 40
        reasons.append("исследование/опрос")
    if CX_RE.search(text):
        score += 35
        reasons.append("CX / обратная связь")
    if HR_RE.search(text):
        score += 35
        reasons.append("HR / сотрудники")
    if PLATFORM_RE.search(text):
        score += 30
        reasons.append("платформа опросов")

    kw = (lead.matched_keyword or "").lower()
    if kw:
        stems = [w for w in re.split(r"[\s\-–—,]+", kw) if len(w) >= 5]
        if any(s in text for s in stems):
            score += 15
            reasons.append(f"ключ «{lead.matched_keyword}»")

    if lead.source == "zakupki":
        score += 10
        reasons.append("ЕИС — надёжный источник")

    if lead.status == TenderStatus.ACTIVE:
        score += 15
        reasons.append("закупка активна")
    elif lead.status == TenderStatus.COMPLETED:
        score -= 5

    if lead.customer_inn:
        score += 5

    if any(c.email or c.phone for c in lead.contacts):
        score += 15
        reasons.append("есть контакт")

    if GOV_RE.search(lead.customer_name or ""):
        score += 10
        reasons.append("госзаказчик → реестр РПО")

    # срочность по end_date (грубо: dd.mm.yyyy в строке)
    days = _days_until(lead.end_date)
    if days is not None:
        if 0 <= days <= 5:
            score += 20
            reasons.append(f"дедлайн через {days} дн.")
        elif days <= 14:
            score += 10
            reasons.append(f"дедлайн через {days} дн.")

    score = max(0, min(100, score))
    if not reasons:
        reasons.append("базовое совпадение")
    return score, segment, reasons


def _days_until(end_date: str | None) -> int | None:
    if not end_date:
        return None
    m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", end_date)
    if not m:
        return None
    try:
        end = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        return (end.date() - datetime.now().date()).days
    except ValueError:
        return None
