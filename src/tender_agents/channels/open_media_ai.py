"""Универсальное извлечение ЛПР из HTML любой страницы (YandexGPT)."""

from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_EXTRACT_INSTRUCTIONS = """Ты — агент FeedBackTalk: извлекаешь людей (ЛПР, HR, руководителей) из материала на русском.

Типы страниц: рейтинги, новости HR-саммитов, интервью, списки спикеров, таблицы, статьи клуба HR.

Правила:
- Только реальные ФИО из текста (минимум имя+фамилия). Не выдумывай.
- company — организация/работодатель; если в тексте нет — null.
- role — должность; если нет — null.
- bio — 1–4 предложения фактов о человеке из статьи (достижения, цитаты, контекст).
- email/phone — только если явно указаны в тексте, иначе null.
- rank — место в рейтинге или null.
- Если страница — **каталог/рейтинг со списком** (десятки имён), верни **всех** упомянутых людей, не только первых пять.

Ответ — только JSON:
{
  "page_summary": "одно предложение о материале",
  "people": [
    {
      "rank": null,
      "name": "Фамилия Имя Отчество",
      "company": "организация или null",
      "role": "должность или null",
      "bio": "факты",
      "email": null,
      "phone": null
    }
  ]
}
Если людей нет — {"page_summary": "...", "people": []}."""


def html_to_extract_text(html: str, *, max_chars: int = 32000) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text[:max_chars]


def _normalize_person(p: dict) -> dict | None:
    if not isinstance(p, dict):
        return None
    name = str(p.get("name") or "").strip()
    parts = name.split()
    if len(parts) < 2:
        return None
    if not re.match(r"^[А-ЯЁA-Z]", parts[0]):
        return None
    company = str(p.get("company") or "").strip() or "—"
    return {
        "name": name[:256],
        "company": company[:512],
        "role": str(p.get("role") or "").strip()[:512],
        "rank": str(p.get("rank") or "").strip() or "—",
        "bio": str(p.get("bio") or "").strip()[:8000],
        "score": p.get("score"),
        "email": str(p.get("email") or "").strip()[:256] or None,
        "phone": str(p.get("phone") or "").strip()[:128] or None,
    }


async def extract_people_with_ai(
    html: str,
    *,
    page_url: str,
    page_title: str = "",
) -> tuple[list[dict], str]:
    """Возвращает (profiles, page_summary)."""
    from tender_agents.yandex.config import is_yandex_configured

    if not is_yandex_configured():
        return [], ""

    try:
        from tender_agents.yandex.client import YandexStudioClient

        client = YandexStudioClient()
        body = html_to_extract_text(html)
        user_input = (
            f"URL: {page_url}\n"
            f"Заголовок: {page_title}\n\n"
            f"Текст страницы:\n{body}"
        )
        data = await client.chat_json(
            instructions=_EXTRACT_INSTRUCTIONS,
            user_input=user_input,
        )
        people = data.get("people") or []
        summary = str(data.get("page_summary") or "").strip()
        out: list[dict] = []
        seen: set[str] = set()
        for p in people:
            row = _normalize_person(p)
            if not row:
                continue
            key = f"{row['name']}|{row['company']}".lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(row)
        return out, summary
    except Exception as e:
        logger.warning("open_media AI extract failed: %s", e)
        return [], ""
