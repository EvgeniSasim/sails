"""Нормализация YANDEX_FOLDER_ID и YANDEX_MODEL (в т.ч. URI gpt://b1…/model)."""

from __future__ import annotations

import re

# ID каталога в Yandex Cloud
_FOLDER_RE = re.compile(r"\bb1[a-z0-9]{20,}\b", re.I)
_GPT_URI_RE = re.compile(r"^gpt://([^/]+)/(.+)$", re.I)

COMMON_MODELS = (
    "yandexgpt",
    "yandexgpt-lite",
    "yandexgpt-pro",
    "yandexgpt/latest",
    "yandexgpt-lite/latest",
    "yandexgpt-pro/latest",
)


def parse_yandex_model_uri(value: str) -> tuple[str, str] | None:
    """
    gpt://b1gai2s8u8p5vdje63jo/yandexgpt → (folder_id, model_name).
    """
    raw = (value or "").strip()
    if not raw.lower().startswith("gpt://"):
        return None
    m = _GPT_URI_RE.match(raw)
    if not m:
        return None
    folder_id = m.group(1).strip()
    model = m.group(2).strip().strip("/")
    if not folder_id or not model:
        return None
    return folder_id, model


def extract_folder_id(value: str) -> str:
    """Только ID каталога: b1g… из строки или из gpt://…"""
    raw = (value or "").strip()
    if not raw:
        return ""
    parsed = parse_yandex_model_uri(raw)
    if parsed:
        return parsed[0]
    m = _FOLDER_RE.search(raw)
    return m.group(0) if m else raw


def resolve_yandex_config(
    folder_id: str,
    model: str,
) -> tuple[str, str]:
    """
    Согласовать поля после загрузки .env или формы настроек.

    Допустимо:
    - YANDEX_FOLDER_ID=b1g… и YANDEX_MODEL=yandexgpt
    - только YANDEX_MODEL=gpt://b1g…/yandexgpt
    - в «Модель» вставили полный URI, Folder ID пустой
    """
    fid = extract_folder_id(folder_id)
    mod = (model or "").strip() or "yandexgpt"

    parsed = parse_yandex_model_uri(mod)
    if parsed:
        uri_folder, uri_model = parsed
        if not fid:
            fid = uri_folder
        mod = uri_model
    elif mod.lower().startswith("gpt://"):
        # битый URI — оставим как есть, folder должен быть задан отдельно
        pass
    elif not fid and _FOLDER_RE.fullmatch(mod):
        fid = mod
        mod = "yandexgpt"

    if mod.lower().startswith("gpt://") and fid:
        again = parse_yandex_model_uri(mod)
        if again:
            mod = again[1]

    return fid, mod


def format_model_uri(folder_id: str, model: str) -> str:
    fid = extract_folder_id(folder_id)
    _, mod = resolve_yandex_config(fid, model)
    if not fid:
        return mod
    return f"gpt://{fid}/{mod}"


def is_yandex_configured(
    *,
    api_key: str | None = None,
    folder_id: str | None = None,
    model: str | None = None,
) -> bool:
    """Достаточно ли настроек для вызовов Yandex GPT (ключ + folder из ID или gpt:// URI)."""
    from tender_agents.settings import settings

    key = (api_key if api_key is not None else settings.yandex_api_key or "").strip()
    if not key:
        return False
    fid, _ = resolve_yandex_config(
        folder_id if folder_id is not None else settings.yandex_folder_id,
        model if model is not None else settings.yandex_model,
    )
    return bool(fid)
