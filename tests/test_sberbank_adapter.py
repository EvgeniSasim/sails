import pytest
from tender_agents.platforms.sberbank_ast import SberbankAstAdapter

def test_normalize_url():
    adapter = SberbankAstAdapter()
    url1 = "HTTPS://www.Sberbank-AST.ru/purchaseview.aspx?id=123#fragment"
    url2 = "https://www.sberbank-ast.ru/purchaseview.aspx?id=123"
    assert adapter._normalize_url(url1) == adapter._normalize_url(url2)

def test_normalize_url_different_query():
    adapter = SberbankAstAdapter()
    url1 = "https://www.sberbank-ast.ru/purchaseview.aspx?id=123"
    url2 = "https://www.sberbank-ast.ru/purchaseview.aspx?id=456"
    assert adapter._normalize_url(url1) != adapter._normalize_url(url2)
