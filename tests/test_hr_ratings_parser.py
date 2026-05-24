"""Парсер hr-ratings.com."""

from __future__ import annotations

from tender_agents.channels.hr_ratings import parse_hr_ratings_html
from tender_agents.channels.people_leads import profiles_to_leads

SAMPLE_HTML = """
<html><body>
<h1>Рейтинг HR 2025</h1>
<h2 class="t220__title t-heading t-heading_sm">1. Наталья Дудина, Сбер</h2>
<div><p>Компания: ПАО Сбербанк. Должность: Старший вице-президент HR. Финансовое влияние: рост retention.</p></div>
<h2 class="t220__title t-heading t-heading_sm">2. Ирина Кабурова, Ozon</h2>
<div><p>Компания: Ozon. Должность: Директор по персоналу.</p></div>
<h2 class="t220__title t-heading t-heading_sm">топ 6-10 HR-лидеры</h2>
<div><p>6. Елена Петрова, HeadHunter (339 баллов) — Директор по персоналу.</p></div>
</body></html>
"""


def test_parse_hr_ratings_html_finds_leaders():
    headline, profiles = parse_hr_ratings_html(
        SAMPLE_HTML, article_url="https://hr-ratings.com/test"
    )
    assert "Рейтинг" in headline
    assert len(profiles) >= 3
    names = {p["name"] for p in profiles}
    assert "Наталья Дудина" in names
    assert "Елена Петрова" in names


def test_profiles_to_leads_open_media():
    _, profiles = parse_hr_ratings_html(SAMPLE_HTML, article_url="https://hr-ratings.com/test")
    leads = profiles_to_leads(
        profiles[:1],
        article_url="https://hr-ratings.com/test",
        headline="Test",
        source="hr_ratings",
        channel_kind="hr_ratings",
    )
    assert leads[0].channel == "open_media"
    assert leads[0].raw_extract.get("channel_kind") == "hr_ratings"
    assert leads[0].contacts[0].name == "Наталья Дудина"
