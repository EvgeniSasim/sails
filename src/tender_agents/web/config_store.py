"""Чтение и запись конфигурации проекта (.env + YAML)."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

from tender_agents.settings import CONFIG_DIR, ROOT, Settings

SECRET_MASK = "••••••••"
UNCHANGED = "__UNCHANGED__"

ENV_KEYS = [
    "SCRAPER_BACKEND",
    "AGENT_PROVIDER",
    "REQUEST_DELAY_SEC",
    "DATABASE_URL",
    "SGAI_API_KEY",
    "YANDEX_API_KEY",
    "YANDEX_FOLDER_ID",
    "YANDEX_MODEL",
    "YANDEX_BASE_URL",
    "YANDEX_USE_RESPONSES_API",
    "YANDEX_ENABLE_WEB_SEARCH",
    "YANDEX_MAX_HTML_CHARS",
    "OLLAMA_BASE_URL",
    "OLLAMA_MODEL",
    "GOSPLAN_API_URL",
    "GOSPLAN_API_KEY",
    "DASHBOARD_HOST",
    "DASHBOARD_PORT",
]


def _env_path() -> Path:
    return ROOT / ".env"


def _parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        out[key.strip()] = val.strip()
    return out


def _write_env_file(values: dict[str, str]) -> None:
    path = _env_path()
    existing = _parse_env_file(path) if path.exists() else {}
    merged = {**existing, **values}
    lines: list[str] = []
    written: set[str] = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                key = line.split("=", 1)[0].strip()
                if key in merged:
                    lines.append(f"{key}={merged[key]}")
                    written.add(key)
                    continue
            lines.append(line)
    for key in ENV_KEYS:
        if key not in written and key in merged:
            lines.append(f"{key}={merged[key]}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return SECRET_MASK
    return value[:4] + SECRET_MASK + value[-2:]


def reload_settings() -> Settings:
    from tender_agents import settings as settings_mod

    settings_mod.settings = Settings()
    return settings_mod.settings


class ConfigStore:
  def load_public_config(self) -> dict[str, Any]:
      s = Settings()
      env = _parse_env_file(_env_path())
      from tender_agents.config_loader import describe_keywords_setup

      kw_setup = describe_keywords_setup()
      keywords = self._load_keywords_raw()
      sources = self._load_sources_raw()
      agents = self._load_agents_raw()
      from tender_agents.yandex.config import is_yandex_configured

      yandex_ok = is_yandex_configured()
      return {
          "scraper_backend": s.scraper_backend,
          "agent_provider": s.agent_provider,
          "request_delay_sec": s.request_delay_sec,
          "database_url": s.database_url,
          "yandex_model": s.yandex_model,
          "yandex_base_url": s.yandex_base_url,
          "yandex_use_responses_api": s.yandex_use_responses_api,
          "yandex_enable_web_search": s.yandex_enable_web_search,
          "yandex_max_html_chars": s.yandex_max_html_chars,
          "yandex_folder_id": s.yandex_folder_id,
          "yandex_api_key_set": bool(s.yandex_api_key),
          "yandex_api_key_mask": mask_secret(s.yandex_api_key),
          "sgai_api_key_set": bool(s.sgai_api_key),
          "sgai_api_key_mask": mask_secret(s.sgai_api_key),
          "gosplan_api_url": s.gosplan_api_url,
          "gosplan_api_key_set": bool(s.gosplan_api_key),
          "gosplan_api_key_mask": mask_secret(s.gosplan_api_key),
          "ollama_base_url": s.ollama_base_url,
          "ollama_model": s.ollama_model,
          "keywords": keywords.get("keywords", []),
          "keywords_merge_extra": keywords.get("merge_extra", False),
          "keywords_effective": kw_setup["effective"],
          "keywords_extra_files": kw_setup["extra"],
          "sources": sources.get("sources", {}),
          "agents": agents.get("agents", {}),
          "channels": self._load_yaml(CONFIG_DIR / "channels.yaml"),
          "yandex_configured": yandex_ok,
      }

  def save_env_settings(
      self,
      *,
      scraper_backend: str,
      agent_provider: str,
      request_delay_sec: float,
      database_url: str,
      yandex_folder_id: str = "",
      yandex_model: str = "yandexgpt",
      yandex_base_url: str = "",
      yandex_use_responses_api: bool = False,
      yandex_enable_web_search: bool = False,
      yandex_max_html_chars: int = 48_000,
      ollama_base_url: str = "",
      ollama_model: str = "",
      gosplan_api_url: str = "",
      yandex_api_key: str = UNCHANGED,
      sgai_api_key: str = UNCHANGED,
      gosplan_api_key: str = UNCHANGED,
  ) -> None:
      from tender_agents.yandex.config import resolve_yandex_config

      y_fid, y_mod = resolve_yandex_config(yandex_folder_id, yandex_model)
      env = _parse_env_file(_env_path())
      updates: dict[str, str] = {
          "SCRAPER_BACKEND": scraper_backend,
          "AGENT_PROVIDER": agent_provider,
          "REQUEST_DELAY_SEC": str(request_delay_sec),
          "DATABASE_URL": database_url,
          "YANDEX_FOLDER_ID": y_fid,
          "YANDEX_MODEL": y_mod,
          "YANDEX_BASE_URL": yandex_base_url or "https://llm.api.cloud.yandex.net/v1",
          "YANDEX_USE_RESPONSES_API": "true" if yandex_use_responses_api else "false",
          "YANDEX_ENABLE_WEB_SEARCH": (
              "true"
              if yandex_enable_web_search and yandex_use_responses_api
              else "false"
          ),
          "YANDEX_MAX_HTML_CHARS": str(yandex_max_html_chars),
          "OLLAMA_BASE_URL": ollama_base_url,
          "OLLAMA_MODEL": ollama_model,
          "GOSPLAN_API_URL": gosplan_api_url,
      }
      for secret_key, form_val, env_key in (
          ("yandex", yandex_api_key, "YANDEX_API_KEY"),
          ("sgai", sgai_api_key, "SGAI_API_KEY"),
          ("gosplan", gosplan_api_key, "GOSPLAN_API_KEY"),
      ):
          if form_val != UNCHANGED and form_val.strip() and SECRET_MASK not in form_val:
              updates[env_key] = form_val.strip()
          elif env_key in env:
              updates[env_key] = env[env_key]
      _write_env_file(updates)
      reload_settings()

  def save_keywords(
      self, keywords: list[str], *, merge_extra: bool = False
  ) -> None:
      path = CONFIG_DIR / "keywords.yaml"
      data = self._load_keywords_raw()
      data["keywords"] = [k.strip() for k in keywords if k.strip()]
      data["merge_extra"] = merge_extra
      path.write_text(
          yaml.dump(data, allow_unicode=True, default_flow_style=False),
          encoding="utf-8",
      )

  def save_sources(self, enabled_ids: list[str]) -> None:
      path = CONFIG_DIR / "sources.yaml"
      data = self._load_sources_raw()
      for sid, cfg in data.get("sources", {}).items():
          cfg["enabled"] = sid in enabled_ids
      path.write_text(
          yaml.dump(data, allow_unicode=True, default_flow_style=False),
          encoding="utf-8",
      )

  def save_agents(
      self,
      *,
      search_instructions: str,
      enrich_instructions: str,
      orchestrator_instructions: str,
  ) -> None:
      path = CONFIG_DIR / "yandex_agents.yaml"
      header = ""
      if path.exists():
          header_lines: list[str] = []
          for line in path.read_text(encoding="utf-8").splitlines():
              if line.strip().startswith("#") or not line.strip():
                  header_lines.append(line)
              else:
                  break
          if header_lines:
              header = "\n".join(header_lines).rstrip() + "\n\n"
      data = {
          "agents": {
              "search": {"instructions": search_instructions.strip()},
              "enrich": {"instructions": enrich_instructions.strip()},
              "orchestrator": {"instructions": orchestrator_instructions.strip()},
          }
      }
      body = yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)
      path.write_text(header + body, encoding="utf-8")

  def _load_keywords_raw(self) -> dict:
      return self._load_yaml(CONFIG_DIR / "keywords.yaml")

  def _load_sources_raw(self) -> dict:
      return self._load_yaml(CONFIG_DIR / "sources.yaml")

  def _load_agents_raw(self) -> dict:
      return self._load_yaml(CONFIG_DIR / "yandex_agents.yaml")

  @staticmethod
  def _load_yaml(path: Path) -> dict:
      if not path.exists():
          return {}
      with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
