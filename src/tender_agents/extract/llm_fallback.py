"""Опциональное извлечение полей тендера через Yandex GPT."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

_MAX_CHARS = 12_000
_COMPLETION_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"


def llm_fallback_enabled(filters_flag: bool = False) -> bool:
    if filters_flag:
        return True
    return os.getenv("TENDER_LEADS_LLM_FALLBACK", "").lower() in ("1", "true", "yes")


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fence:
        text = fence.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    return json.loads(text)


async def extract_tender_from_text(text: str, url: str) -> dict[str, Any]:
    """Вернуть поля тендера из текста страницы через Yandex Completion API."""
    api_key = os.getenv("YANDEX_API_KEY")
    folder_id = os.getenv("YANDEX_FOLDER_ID")
    model = os.getenv("YANDEX_MODEL", "yandexgpt-lite")

    if not api_key or not folder_id:
        logger.warning(
            "LLM fallback пропущен: задайте YANDEX_API_KEY и YANDEX_FOLDER_ID в окружении"
        )
        return {}

    try:
        import httpx
    except ImportError:
        logger.warning("LLM fallback пропущен: pip install -e '.[llm]'")
        return {}

    snippet = text[:_MAX_CHARS]
    prompt = (
        "Извлеки данные о тендере из текста страницы. "
        "Верни только JSON без пояснений с ключами: "
        "external_id, title, customer_name, price, publish_date, deadline, contacts. "
        "Даты в формате ГГГГ-ММ-ДД или null. "
        f"URL: {url}\n\nТекст:\n{snippet}"
    )

    body = {
        "modelUri": f"gpt://{folder_id}/{model}",
        "completionOptions": {"stream": False, "temperature": 0.1, "maxTokens": 800},
        "messages": [{"role": "user", "text": prompt}],
    }

    headers = {
        "Authorization": f"Api-Key {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(_COMPLETION_URL, headers=headers, json=body)
        resp.raise_for_status()
        payload = resp.json()

    result_text = (
        payload.get("result", {}).get("alternatives", [{}])[0]
        .get("message", {})
        .get("text", "")
    )
    if not result_text:
        return {}

    try:
        data = _extract_json(result_text)
        return {k: v for k, v in data.items() if v}
    except json.JSONDecodeError:
        logger.warning("LLM fallback: не удалось разобрать JSON из ответа")
        return {}
