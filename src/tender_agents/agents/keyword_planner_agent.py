"""Агент: задача менеджера → список ключевых слов для поиска закупок."""

from __future__ import annotations

import logging
import re

from tender_agents.config_loader import load_keywords_raw, _load_yaml_keywords
from tender_agents.settings import CONFIG_DIR

logger = logging.getLogger(__name__)

_KEYWORD_PLANNER_INSTRUCTIONS = """Ты планируешь ключевые слова для поиска госзакупок платформы FeedBackTalk (опросы, HR-пульс, CX, исследования).
Ответ — только JSON:
{"keywords": ["..."], "segment_hints": {"фраза": "hr|cx|research|gov|other"}, "notes": "кратко"}
Исключи CRM, 1С, канцелярию, мебель. 8–20 фраз на русском."""

# Эвристика по словам в задаче
_TOPIC_MAP = [
    (r"(?i)hr|персонал|сотрудник|enps|360|вовлеч", "hr", ["eNPS", "HR опрос", "пульс-опрос", "оценка 360", "мониторинг вовлеченности"]),
    (r"(?i)cx|клиентск|nps|csat|voc|лояльност", "cx", ["NPS", "CSAT", "Voice of Customer", "клиентский опыт", "обратная связь клиентов"]),
    (r"(?i)исследован|социолог|анкетир|фокус", "research", ["маркетинговое исследование", "социологическое исследование", "анкетирование"]),
    (r"(?i)гос|44-фз|223|муниципал|бюджет", "gov", ["платформа опросов", "проведение онлайн опросов", "электронный опрос"]),
]
_DEFAULT = [
    "проведение онлайн опросов",
    "платформа опросов",
    "пульс-опрос",
    "eNPS",
    "NPS",
    "маркетинговое исследование",
]


def _heuristic_keywords(task: str, existing: list[str], *, merge_hr_cx: bool) -> dict:
    text = (task or "").strip()
    found: list[str] = []
    hints: dict[str, str] = {}
    for pattern, seg, phrases in _TOPIC_MAP:
        if re.search(pattern, text):
            for p in phrases:
                if p not in found:
                    found.append(p)
                    hints[p] = seg
    if not found:
        found = list(_DEFAULT)
        for p in found:
            hints[p] = "cx"
    if merge_hr_cx:
        for name in ("keywords_hr.yaml", "keywords_cx.yaml"):
            for k in _load_yaml_keywords(CONFIG_DIR / name):
                if k not in found:
                    found.append(k)
                    hints[k] = "hr" if "hr" in name else "cx"
    for e in existing:
        if e not in found:
            found.append(e)
    return {
        "keywords": found[:20],
        "segment_hints": hints,
        "notes": "Список собран эвристикой по тексту задачи (Yandex API не использовался или недоступен).",
    }


async def plan_keywords(
    task: str,
    *,
    existing: list[str] | None = None,
    merge_hr_cx: bool = False,
    use_yandex: bool = True,
) -> dict:
    """Возвращает {keywords, segment_hints, notes}."""
    existing = existing or [str(k).strip() for k in load_keywords_raw().get("keywords", []) if str(k).strip()]
    if not (task or "").strip():
        return _heuristic_keywords("", existing, merge_hr_cx=merge_hr_cx)

    if use_yandex:
        from tender_agents.yandex.config import is_yandex_configured

        if is_yandex_configured():
            try:
                from tender_agents.yandex.client import YandexStudioClient

                client = YandexStudioClient()
                user_input = (
                    f"Задача менеджера: {task.strip()}\n"
                    f"Уже в списке (не дублировать): {', '.join(existing[:30])}\n"
                    f"Добавить HR/CX файлы: {merge_hr_cx}"
                )
                data = await client.chat_json(
                    instructions=_KEYWORD_PLANNER_INSTRUCTIONS,
                    user_input=user_input,
                )
                kws = [str(x).strip() for x in (data.get("keywords") or []) if str(x).strip()]
                if kws:
                    return {
                        "keywords": kws[:20],
                        "segment_hints": data.get("segment_hints") or {},
                        "notes": str(data.get("notes") or "Сгенерировано YandexGPT."),
                    }
            except Exception as e:
                logger.warning("Keyword planner Yandex failed: %s", e)

    return _heuristic_keywords(task, existing, merge_hr_cx=merge_hr_cx)
