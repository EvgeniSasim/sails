"""Универсальный ingest: неизвестный хост → AI."""

from __future__ import annotations

import pytest

SAMPLE_NEWS_HTML = """
<html><head><title>HR Club News</title></head><body>
<h1>Встреча HR-директоров</h1>
<p>Иван Петров, директор по персоналу ООО Ромашка, рассказал о eNPS.</p>
<p>Мария Сидорова из ПАО Вектор — о цифровизации HR.</p>
</body></html>
"""


@pytest.mark.asyncio
async def test_ingest_unknown_host_uses_ai(monkeypatch):
    from tender_agents.channels import ingest as ing

    async def fake_fetch(url: str) -> str:
        return SAMPLE_NEWS_HTML

    async def fake_ai(html, *, page_url, page_title=""):
        return [
            {
                "name": "Иван Петров",
                "company": "ООО Ромашка",
                "role": "директор по персоналу",
                "rank": "—",
                "bio": "рассказал о eNPS",
            },
            {
                "name": "Мария Сидорова",
                "company": "ПАО Вектор",
                "role": "",
                "rank": "—",
                "bio": "цифровизация HR",
            },
        ], "Новость HR club"

    monkeypatch.setattr(
        "tender_agents.channels.page_fetch.fetch_page_html",
        fake_fetch,
    )
    monkeypatch.setattr(
        "tender_agents.channels.open_media_ai.extract_people_with_ai",
        fake_ai,
    )
    monkeypatch.setattr(
        "tender_agents.yandex.config.is_yandex_configured",
        lambda: True,
    )

    leads = await ing.ingest_url("https://hrsummit.ru/hrclubnews/27092021")
    assert len(leads) == 2
    assert leads[0].channel == "open_media"
    assert leads[0].raw_extract.get("channel_kind") == "ai_open_media"


@pytest.mark.asyncio
async def test_ingest_unknown_host_requires_yandex(monkeypatch):
    from tender_agents.channels import ingest as ing

    monkeypatch.setattr(
        "tender_agents.channels.page_fetch.fetch_page_html",
        lambda u: SAMPLE_NEWS_HTML,
    )
    monkeypatch.setattr(
        "tender_agents.yandex.config.is_yandex_configured",
        lambda: False,
    )

    with pytest.raises(ValueError, match="YandexGPT"):
        await ing.ingest_url("https://hrsummit.ru/hrclubnews/27092021")
