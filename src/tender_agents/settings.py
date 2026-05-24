from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # httpx (free) | playwright | crawl4ai | scrapegraph
    scraper_backend: str = "httpx"

    sgai_api_key: str = ""
    database_url: str = "sqlite+aiosqlite:///./data/leads.db"
    request_delay_sec: float = 2.0
    scrapegraph_base_url: str = "https://v2-api.scrapegraphai.com/api"

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2"

    gosplan_api_url: str = "https://v2test.gosplan.info"
    gosplan_api_key: str = ""

    # Yandex AI Studio — https://aistudio.yandex.ru/ru/developers
    yandex_api_key: str = ""
    yandex_folder_id: str = ""
    yandex_model: str = "yandexgpt"
    yandex_base_url: str = "https://llm.api.cloud.yandex.net/v1"
    # У llm.api.cloud.yandex.net/v1 нет /responses — только chat/completions
    yandex_use_responses_api: bool = False
    yandex_enable_web_search: bool = False
    yandex_max_html_chars: int = 48_000

    # agent_provider: local | yandex — запуск LLM-агентов через Yandex
    agent_provider: str = "local"

    dashboard_host: str = "127.0.0.1"
    dashboard_port: int = 8765

    @model_validator(mode="after")
    def _normalize_yandex(self) -> "Settings":
        from tender_agents.yandex.config import resolve_yandex_config

        fid, mod = resolve_yandex_config(self.yandex_folder_id, self.yandex_model)
        self.yandex_folder_id = fid
        self.yandex_model = mod
        return self


settings = Settings()
