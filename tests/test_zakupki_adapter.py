from pathlib import Path

from tender_agents.platforms.zakupki import parse_detail_html, parse_listing_html

FIXTURES = Path(__file__).parent / "fixtures" / "zakupki"


def test_parse_listing_from_fixture():
    html = (FIXTURES / "search_crm.html").read_text(encoding="utf-8")
    items = parse_listing_html(html)
    assert len(items) >= 2
    assert items[0]["external_id"] == "0123456789012345678"
    assert "CRM" in items[0]["title"]
    assert "regNumber=0123456789012345678" in items[0]["url"]


def test_parse_detail_minimal():
    html = """
    <html><body>
    Реестровый номер 0123456789012345678
    <div class="cardMainInfo__content">Услуги CRM</div>
    Размещено 01.02.2024
    Начальная (максимальная) цена контракта 500 000,00
    </body></html>
    """
    fields = parse_detail_html(
        html,
        url="https://zakupki.gov.ru/epz/order/notice/ea20/view/common-info.html?regNumber=0123456789012345678",
    )
    assert fields["external_id"] == "0123456789012345678"
    assert fields["title"] == "Услуги CRM"
    assert fields["publish_date_str"] == "01.02.2024"


def test_zakupki_matches_url():
    from tender_agents.platforms.zakupki import ZakupkiAdapter

    adapter = ZakupkiAdapter()
    assert adapter.matches_url("https://zakupki.gov.ru/")
    assert not adapter.matches_url("https://www.sberbank-ast.ru/")
    assert adapter.needs_browser is False
