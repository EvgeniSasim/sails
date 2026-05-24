"""E2E-style tests: zakupki period → build_search_url + orchestrator post-filter (mock HTTP)."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from tender_agents.agents.orchestrator import Orchestrator
from tender_agents.db import LeadRepository
from tender_agents.models import SearchResultItem, TenderLead, TenderStatus
from tender_agents.scrape.parsers import zakupki as zakupki_parser

_SEARCH_HTML = """
<html><body>
<div class="search-registry-entry-block">
  <div class="registry-entry__body-value">Услуги по проведению опроса удовлетворённости</div>
  <div class="registry-entry__header-mid__number">№ 1234567890123456789</div>
  <div class="registry-entry__body-href"><a href="#">ООО Тест</a></div>
  <a href="/epz/order/notice/ea20/view/common-info.html?regNumber=1234567890123456789">карточка</a>
</div>
</body></html>
"""


class _FakeResponse:
    def __init__(self, text: str, url: str) -> None:
        self.text = text
        self.status_code = 200
        self.request = httpx.Request("GET", url)

    def raise_for_status(self) -> None:
        return None


@pytest.mark.asyncio
async def test_zakupki_search_passes_period_to_build_search_url():
    captured: list[str] = []
    period_from = date.today() - timedelta(days=7)

    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url: str):
            captured.append(url)
            return _FakeResponse(_SEARCH_HTML, url)

    with patch("tender_agents.scrape.parsers.zakupki.httpx.AsyncClient", return_value=_FakeClient()):
        items = await zakupki_parser.search(
            "опрос",
            max_pages=1,
            date_from=period_from,
            date_to=date.today(),
        )

    assert len(items) >= 1
    assert captured
    assert "publishDateFrom=" in captured[0]
    assert period_from.strftime("%d.%m.%Y") in captured[0]
    assert "publishDateTo=" in captured[0]


def test_build_search_url_includes_publish_dates():
    d_from = date(2026, 5, 1)
    d_to = date(2026, 5, 24)
    url = zakupki_parser.build_search_url("crm", date_from=d_from, date_to=d_to)
    assert "publishDateFrom=01.05.2026" in url
    assert "publishDateTo=24.05.2026" in url


@pytest.mark.asyncio
async def test_orchestrator_post_filter_period_days(tmp_path, monkeypatch):
    """CLI run -s zakupki --period-days 7: лиды вне периода отбрасываются после enrich."""
    db_path = tmp_path / "leads.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")

    period_days = 7
    d_from = date.today() - timedelta(days=period_days)

    item = SearchResultItem(
        title="Опрос удовлетворённости клиентов",
        url="https://zakupki.gov.ru/epz/order/notice/ea20/view/common-info.html?regNumber=1",
        external_id="1",
    )

    old_lead = TenderLead(
        source="zakupki",
        external_id="old",
        title="Старый",
        url="https://example.com/old",
        status=TenderStatus.UNKNOWN,
        matched_keyword="опрос",
        publish_date="2020-01-15",
    )
    new_lead = TenderLead(
        source="zakupki",
        external_id="new",
        title="Свежий",
        url="https://example.com/new",
        status=TenderStatus.UNKNOWN,
        matched_keyword="опрос",
        publish_date=date.today().isoformat(),
    )

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from tender_agents.orm import Base
    from tender_agents.sources.zakupki import ZakupkiAdapter

    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    repo = LeadRepository(factory, engine)

    adapter = ZakupkiAdapter(
        {"name": "ЕИС", "search_url": "https://zakupki.gov.ru/epz/order/extendedsearch/results.html"},
        backend=MagicMock(name="httpx"),
    )

    orch = Orchestrator(
        keywords=["опрос"],
        source_ids=["zakupki"],
        backend=MagicMock(name="httpx"),
        repo=repo,
        date_from=d_from,
        date_to=None,
    )
    orch.adapters = [adapter]
    orch.search_agent.adapters = [adapter]

    monkeypatch.setattr(
        orch.search_agent,
        "run",
        AsyncMock(return_value=[(adapter, "опрос", item)]),
    )
    monkeypatch.setattr(
        orch.enrich_agent,
        "run",
        AsyncMock(return_value=[old_lead, new_lead]),
    )

    stats = await orch.run_pipeline(max_per_keyword=5, skip_enrich=False)

    assert stats["stored"] == 1
    assert stats["date_from"] == d_from.isoformat()
