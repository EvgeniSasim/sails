import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from tender_agents.extract.llm_fallback import extract_tender_from_text, llm_fallback_enabled


def test_llm_fallback_enabled_env(monkeypatch):
    monkeypatch.delenv("TENDER_LEADS_LLM_FALLBACK", raising=False)
    assert llm_fallback_enabled(False) is False
    monkeypatch.setenv("TENDER_LEADS_LLM_FALLBACK", "1")
    assert llm_fallback_enabled(False) is True
    assert llm_fallback_enabled(True) is True


@pytest.mark.asyncio
async def test_extract_tender_from_text_mock(monkeypatch):
    monkeypatch.setenv("YANDEX_API_KEY", "test-key")
    monkeypatch.setenv("YANDEX_FOLDER_ID", "folder")

    payload = {
        "result": {
            "alternatives": [
                {
                    "message": {
                        "text": json.dumps(
                            {
                                "external_id": "123",
                                "title": "CRM услуги",
                                "customer_name": "ООО Тест",
                            }
                        )
                    }
                }
            ]
        }
    }

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = payload

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("httpx.AsyncClient", return_value=mock_client):
        data = await extract_tender_from_text("обрывок страницы", "https://example.com")

    assert data["external_id"] == "123"
    assert data["title"] == "CRM услуги"
    assert data["customer_name"] == "ООО Тест"
