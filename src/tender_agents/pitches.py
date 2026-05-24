"""Шаблоны питча FeedBackTalk по сегменту лида."""

from __future__ import annotations

from tender_agents.models import LeadSegment, TenderLead

BASE = (
    "FeedBackTalk (https://feedbacktalk.ru/) — российская платформа CX, опросов и обратной связи. "
    "В реестре отечественного ПО. Облако или on-prem."
)


PITCHES: dict[LeadSegment, str] = {
    LeadSegment.RESEARCH: (
        "{base}\n\n"
        "Видим вашу закупку на исследование/опрос. Предлагаем платформу вместо разового подрядного отчёта: "
        "конструктор опросов, сегментация, кампании, аналитика в реальном времени.\n\n"
        "Заказчик: {customer}\n"
        "Предмет: {title}\n"
        "Ссылка: {url}"
    ),
    LeadSegment.CX: (
        "{base}\n\n"
        "Для задач клиентского опыта и обратной связи: NPS/CSAT/CES, омниканальные опросы, "
        "профиль клиента, ИИ-инсайты. Импортозамещение зарубежных CX-платформ.\n\n"
        "Заказчик: {customer}\n"
        "Предмет: {title}\n"
        "Ссылка: {url}"
    ),
    LeadSegment.HR: (
        "{base}\n\n"
        "Для HR: пульс-опросы, eNPS, оценка 360, мониторинг вовлечённости, анонимная обратная связь "
        "от сотрудников с отчётами для руководства.\n\n"
        "Заказчик: {customer}\n"
        "Предмет: {title}\n"
        "Ссылка: {url}"
    ),
    LeadSegment.GOV: (
        "{base}\n\n"
        "Для госказазчика: соответствие 44-ФЗ/223-ФЗ, отечественное ПО из реестра, "
        "проведение опросов граждан/клиентов услуг с защитой данных (152-ФЗ).\n\n"
        "Заказчик: {customer}\n"
        "Предмет: {title}\n"
        "Ссылка: {url}"
    ),
    LeadSegment.OTHER: (
        "{base}\n\n"
        "Готовы провести демо платформы под вашу закупку.\n\n"
        "Заказчик: {customer}\n"
        "Предмет: {title}\n"
        "Ссылка: {url}"
    ),
}


def build_pitch(lead: TenderLead, segment: LeadSegment) -> str:
    ctx = ""
    if lead.channel == "open_media" and lead.context_title:
        ctx = (
            f"Контекст: публикация «{lead.context_title}»"
            + (f" ({lead.context_url})" if lead.context_url else "")
            + ".\n\n"
        )
    tpl = PITCHES.get(segment, PITCHES[LeadSegment.OTHER])
    return ctx + tpl.format(
        base=BASE,
        customer=lead.customer_name or "—",
        title=lead.title,
        url=lead.url,
    )
