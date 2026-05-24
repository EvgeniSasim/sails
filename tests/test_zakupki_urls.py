"""Unit tests for zakupki URL helpers (no network)."""

from tender_agents.scrape.parsers.zakupki import detail_url_candidates, normalize_detail_url


def test_detail_url_candidates_includes_common_info_for_printform():
    url = (
        "https://zakupki.gov.ru/epz/order/notice/notice223-new/printForm/view.html"
        "?regNumber=0123456789012345678"
    )
    cands = detail_url_candidates(url)
    assert any("common-info.html" in u for u in cands)
    assert any("regNumber=0123456789012345678" in u for u in cands)
    assert cands[0] != url or "common-info" in cands[0]


def test_normalize_detail_url_prefers_common_info():
    printform = (
        "https://zakupki.gov.ru/epz/order/notice/ea20/view/printForm/view.html"
        "?regNumber=09998887776665554433"
    )
    norm = normalize_detail_url(printform)
    assert "printForm" not in norm or "common-info" in norm


def test_candidates_order_printform_last():
    url = (
        "https://zakupki.gov.ru/epz/order/notice/notice223-new/printForm/view.html"
        "?regNumber=0111222333444555666"
    )
    cands = detail_url_candidates(url)
    non_pf = [u for u in cands if "printForm" not in u]
    pf = [u for u in cands if "printForm" in u]
    if non_pf and pf:
        assert cands.index(non_pf[0]) < cands.index(pf[0])
