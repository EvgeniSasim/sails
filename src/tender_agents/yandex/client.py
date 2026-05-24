"""Клиент Yandex Cloud AI Studio (OpenAI-compatible API).

Документация: https://yandex.cloud/ru/docs/ai-studio/
Ключ API: https://aistudio.yandex.ru/ru/developers
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from tender_agents.settings import settings
from tender_agents.yandex.config import resolve_yandex_config

logger = logging.getLogger(__name__)

_JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.I)


class YandexStudioError(RuntimeError):
    pass


def _is_responses_unavailable(exc: BaseException) -> bool:
    """OpenAI SDK: 404 на /responses у Yandex Cloud LLM API."""
    try:
        from openai import NotFoundError

        if isinstance(exc, NotFoundError):
            return True
    except ImportError:
        pass
    if getattr(exc, "status_code", None) == 404:
        return True
    msg = str(exc).lower()
    return "404" in msg and "not found" in msg


class YandexStudioClient:
    """Обёртка над https://llm.api.cloud.yandex.net/v1 (Responses + Chat Completions)."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        folder_id: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ):
        self.api_key = api_key or settings.yandex_api_key
        fid, mdl = resolve_yandex_config(
            folder_id or settings.yandex_folder_id,
            model or settings.yandex_model,
        )
        self.folder_id = fid
        self.model = mdl
        self.base_url = (base_url or settings.yandex_base_url).rstrip("/")
        self._openai = None

    def _ensure_configured(self) -> None:
        if not self.api_key:
            raise YandexStudioError(
                "YANDEX_API_KEY не задан. Создайте ключ: "
                "https://aistudio.yandex.ru/ru/developers"
            )
        if not self.folder_id:
            raise YandexStudioError(
                "YANDEX_FOLDER_ID не задан. Укажите ID каталога (b1g…) в настройках → API → Folder ID "
                "или вставьте полный URI в «Модель»: gpt://b1g…/yandexgpt"
            )

    @property
    def model_uri(self) -> str:
        from tender_agents.yandex.config import format_model_uri

        return format_model_uri(self.folder_id, self.model)

    def _get_openai_client(self):
        self._ensure_configured()
        if self._openai is None:
            try:
                import openai
            except ImportError as e:
                raise ImportError(
                    "Установите: pip install -e '.[yandex]'"
                ) from e
            self._openai = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                project=self.folder_id,
            )
        return self._openai

    @staticmethod
    def parse_json_response(text: str) -> dict[str, Any]:
        text = text.strip()
        m = _JSON_FENCE.search(text)
        if m:
            text = m.group(1).strip()
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else {"data": data}
        except json.JSONDecodeError:
            # попытка вырезать первый JSON-объект
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                return json.loads(text[start : end + 1])
            raise YandexStudioError(f"Не удалось разобрать JSON от модели: {text[:200]}...")

    def _chat_completion_sync(
        self,
        *,
        instructions: str,
        user_input: str,
        temperature: float = 0.2,
    ) -> str:
        client = self._get_openai_client()
        response = client.chat.completions.create(
            model=self.model_uri,
            temperature=temperature,
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": user_input},
            ],
        )
        choice = response.choices[0]
        return (choice.message.content or "").strip()

    def _responses_create_sync(
        self,
        *,
        instructions: str,
        user_input: str,
        tools: list[dict[str, Any]] | None = None,
    ) -> str:
        client = self._get_openai_client()
        kwargs: dict[str, Any] = {
            "model": self.model_uri,
            "instructions": instructions,
            "input": user_input,
        }
        if tools:
            kwargs["tools"] = tools
        response = client.responses.create(**kwargs)
        if hasattr(response, "output_text") and response.output_text:
            return response.output_text.strip()
        # fallback
        return json.dumps(response.model_dump(), ensure_ascii=False)

    async def chat_json(
        self,
        *,
        instructions: str,
        user_input: str,
        use_responses_api: bool | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        use_responses = (
            use_responses_api
            if use_responses_api is not None
            else settings.yandex_use_responses_api
        )
        if tools and not use_responses:
            logger.warning(
                "web_search tools требуют Responses API; у Yandex LLM API его нет — tools игнорируются"
            )
            tools = None

        def _chat_sync() -> str:
            return self._chat_completion_sync(
                instructions=instructions,
                user_input=user_input,
            )

        def _responses_sync() -> str:
            return self._responses_create_sync(
                instructions=instructions,
                user_input=user_input,
                tools=tools,
            )

        if use_responses:
            try:
                text = await asyncio.to_thread(_responses_sync)
            except Exception as e:
                if _is_responses_unavailable(e):
                    logger.warning(
                        "Responses API недоступен (%s), fallback на chat/completions",
                        e,
                    )
                    text = await asyncio.to_thread(_chat_sync)
                else:
                    raise
        else:
            text = await asyncio.to_thread(_chat_sync)
        return self.parse_json_response(text)

    async def health_check(self) -> dict[str, str]:
        """Проверка ключа и доступа к модели."""
        reply = await asyncio.to_thread(
            self._chat_completion_sync,
            instructions="Ответь одним словом: OK",
            user_input="ping",
            temperature=0,
        )
        return {"status": "ok", "reply": reply[:50], "model": self.model_uri}
