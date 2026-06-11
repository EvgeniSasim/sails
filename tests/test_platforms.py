import pytest
from tender_agents.platforms.registry import get_adapter
from tender_agents.platforms.sberbank_ast import SberbankAstAdapter

def test_registry_sberbank():
    url = "https://www.sberbank-ast.ru/purchaseList.aspx"
    adapter = get_adapter(url)
    assert adapter is not None
    assert isinstance(adapter, SberbankAstAdapter)

def test_adapter_matches():
    adapter = SberbankAstAdapter()
    assert adapter.matches_url("https://www.sberbank-ast.ru/")
    assert adapter.matches_url("http://sberbank-ast.ru/any")
    assert not adapter.matches_url("https://google.com")
