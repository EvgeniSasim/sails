"""Yandex AI Studio — ленивый импорт, чтобы не было цикла settings ↔ client."""

from __future__ import annotations

__all__ = ["YandexStudioClient", "YandexAgentRunner"]


def __getattr__(name: str):
    if name == "YandexStudioClient":
        from tender_agents.yandex.client import YandexStudioClient

        return YandexStudioClient
    if name == "YandexAgentRunner":
        from tender_agents.yandex.agent_runner import YandexAgentRunner

        return YandexAgentRunner
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
