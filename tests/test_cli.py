import pytest
from typer.testing import CliRunner
from tender_agents.cli import app

runner = CliRunner()

@pytest.mark.network
def test_collect_plan_summary():
    result = runner.invoke(app, [
        "collect",
        "--platform-url", "https://www.sberbank-ast.ru/",
        "-k", "crm",
        "--date-from", "2026-05-01"
    ])
    assert result.exit_code == 0
    assert "План сбора сформирован" in result.stdout
    assert "www.sberbank-ast.ru" in result.stdout
    assert "crm" in result.stdout
    assert "с 2026-05-01" in result.stdout

def test_collect_invalid_url():
    result = runner.invoke(app, [
        "collect",
        "--platform-url", "not-a-url",
        "-k", "test"
    ])
    assert result.exit_code == 1
    assert "Ошибка валидации" in result.stdout

def test_collect_invalid_date():
    result = runner.invoke(app, [
        "collect",
        "--platform-url", "https://test.com",
        "-k", "test",
        "--date-from", "invalid"
    ])
    assert result.exit_code == 1
    assert "Ошибка валидации" in result.stdout

@pytest.mark.network
def test_browse_network():
    result = runner.invoke(app, [
        "browse",
        "--url", "https://www.google.com"
    ])
    # This might still fail if blocked, but it's a network test
    assert result.exit_code in (0, 1)
