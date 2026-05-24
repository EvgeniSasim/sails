"""Каталоги персон (globalmsk и аналоги)."""

from tender_agents.channels.listing_extract import (
    discover_catalog_page_urls,
    parse_person_listing_html,
    try_extract_listing,
)

SAMPLE = """
<html><body>
<a href="/person/id/6485">ИСМАГУЛОВ Марат Равильевич</a>
<div><div>ИСМАГУЛОВ Марат Равильевич
Директор по персоналу Альфа-Банка
Альфа-Банк
Читать далее</div></div>
<a href="/person/id/14364">КУРНИКОВА Анастасия</a>
<div><div>КУРНИКОВА Анастасия
HR-менеджер PR Partner
PR Partner
Читать далее</div></div>
</body></html>
"""


def test_parse_person_listing():
    profiles = parse_person_listing_html(
        SAMPLE, page_url="https://globalmsk.ru/person/cat/0/344"
    )
    assert len(profiles) == 2
    names = {p["name"] for p in profiles}
    assert any("Марат" in n for n in names)
    assert any("Анастасия" in n for n in names)


def test_try_extract_requires_min_links():
    assert try_extract_listing("<html><body></body></html>", page_url="https://x.ru") == []


def test_discover_pagination_urls():
    html = """
    <html><body>
    <div class="pager">
      <a href="/person/cat/0/344">1</a>
      <a href="/person/cat/0/344?offset=2">2</a>
      <a href="/person/cat/0/344?offset=3">3</a>
    </div>
    </body></html>
    """
    urls = discover_catalog_page_urls(
        html, page_url="https://globalmsk.ru/person/cat/0/344"
    )
    assert "https://globalmsk.ru/person/cat/0/344?offset=2" in urls
    assert "https://globalmsk.ru/person/cat/0/344?offset=3" in urls
    assert len(urls) >= 3
