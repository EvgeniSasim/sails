"""Аналитика истории тендеров за период — отчёт для менеджера."""

from __future__ import annotations

import logging
from collections import Counter
from datetime import date
from typing import Any

from tender_agents.db import LeadFilters, LeadRepository

logger = logging.getLogger(__name__)

_ANALYST_INSTRUCTIONS = """Ты аналитик закупок FeedBackTalk (опросы, HR, CX).
По JSON-сводке тендеров дай краткий отчёт менеджеру на русском.
Ответ — только JSON:
{"summary": "2-4 предложения", "top_customers": ["..."], "keyword_recommendations": ["..."], "platform_notes": "..."}"""


async def analyze_tender_history(
    repo: LeadRepository,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 500,
    use_yandex: bool = True,
) -> dict[str, Any]:
    flt = LeadFilters(channel="tender", date_from=date_from, date_to=date_to)
    leads = await repo.list_filtered(flt, limit=limit, sort_by="score", order="desc")

    by_segment = Counter(L.segment.value for L in leads)
    by_source = Counter(L.source for L in leads)
    by_customer = Counter(
        (L.customer_name or "—")[:120] for L in leads if L.customer_name
    )
    by_keyword = Counter(L.matched_keyword or "—" for L in leads)
    hot = [L for L in leads if (L.score or 0) >= 60]

    stats = {
        "total": len(leads),
        "hot_count": len(hot),
        "date_from": date_from.isoformat() if date_from else None,
        "date_to": date_to.isoformat() if date_to else None,
        "by_segment": dict(by_segment.most_common(8)),
        "by_source": dict(by_source.most_common(8)),
        "top_customers": [c for c, _ in by_customer.most_common(15)],
        "top_keywords": [k for k, _ in by_keyword.most_common(15)],
        "sample_titles": [L.title[:100] for L in hot[:8]],
    }

    report: dict[str, Any] = {
        "stats": stats,
        "summary": "",
        "keyword_recommendations": [],
        "platform_notes": "",
    }

    if use_yandex:
        from tender_agents.yandex.config import is_yandex_configured

        if is_yandex_configured():
            try:
                from tender_agents.yandex.client import YandexStudioClient

                client = YandexStudioClient()
                import json

                data = await client.chat_json(
                    instructions=_ANALYST_INSTRUCTIONS,
                    user_input=json.dumps(stats, ensure_ascii=False)[:12000],
                )
                report["summary"] = str(data.get("summary") or "")
                report["keyword_recommendations"] = data.get("keyword_recommendations") or []
                report["platform_notes"] = str(data.get("platform_notes") or "")
                if data.get("top_customers"):
                    report["stats"]["top_customers"] = data["top_customers"]
                return report
            except Exception as e:
                logger.warning("Tender analyst Yandex failed: %s", e)

    report["summary"] = (
        f"За период в выборке {stats['total']} тендеров, из них {stats['hot_count']} со скором ≥60. "
        f"Лидеры сегментов: {', '.join(f'{k}({v})' for k, v in by_segment.most_common(3)) or '—'}."
    )
    report["keyword_recommendations"] = [k for k, _ in by_keyword.most_common(5) if k != "—"]
    report["platform_notes"] = (
        "Рекомендуется держать zakupki + httpx; для B2B — playwright при стабильной сети."
    )
    return report
