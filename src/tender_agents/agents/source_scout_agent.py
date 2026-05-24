"""Разведка новой площадки: URL → JSON-спека адаптера."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from urllib.parse import urlparse

from tender_agents.settings import CONFIG_DIR

logger = logging.getLogger(__name__)

_SCOUT_INSTRUCTIONS = """Ты помогаешь добавить площадку закупок в парсер FeedBackTalk.
По URL и фрагменту HTML предложи спецификацию адаптера.
Ответ — только JSON:
{
  "source_id": "snake_case",
  "name": "человекочитаемое",
  "base_url": "https://...",
  "search_url": "https://.../search?q={keyword}",
  "list_selectors": {"item": "...", "title": "...", "link": "..."},
  "notes": "как проверить вручную",
  "risk": "js_required|captcha|ok"
}"""


def _heuristic_spec(url: str, html_snippet: str = "") -> dict:
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower().replace("www.", "")
    sid = re.sub(r"[^a-z0-9]+", "_", host.split(".")[0])[:32] or "new_source"
    base = f"{parsed.scheme}://{parsed.netloc}"
    return {
        "source_id": sid,
        "name": host,
        "base_url": base,
        "search_url": url.strip(),
        "list_selectors": {
            "item": "a[href*='tender'], .search-result, .lot-item",
            "title": "a, h2, h3",
            "link": "a@href",
        },
        "notes": (
            "Черновик по домену. Проверьте search URL в браузере и уточните селекторы. "
            f"HTML sample: {len(html_snippet)} bytes."
        ),
        "risk": "js_required" if "react" in html_snippet.lower()[:5000] else "ok",
    }


async def scout_source(
    url: str,
    *,
    html_snippet: str = "",
    use_yandex: bool = True,
) -> dict:
    url = url.strip()
    if not url.startswith("http"):
        raise ValueError("Нужен полный URL (https://…)")

    snippet = (html_snippet or "")[:8000]
    if not snippet:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                r = await client.get(url)
                snippet = r.text[:8000]
        except Exception as e:
            logger.warning("Source scout fetch failed: %s", e)

    if use_yandex:
        from tender_agents.yandex.config import is_yandex_configured

        if is_yandex_configured():
            try:
                from tender_agents.yandex.client import YandexStudioClient

                client = YandexStudioClient()
                data = await client.chat_json(
                    instructions=_SCOUT_INSTRUCTIONS,
                    user_input=f"URL: {url}\n\nHTML:\n{snippet[:6000]}",
                )
                if data.get("source_id"):
                    return data
            except Exception as e:
                logger.warning("Source scout Yandex failed: %s", e)

    return _heuristic_spec(url, snippet)


def save_spec_to_sources_d(spec: dict) -> Path:
    """Сохранить JSON в config/sources.d/ (не включает в сбор автоматически)."""
    out_dir = CONFIG_DIR / "sources.d"
    out_dir.mkdir(parents=True, exist_ok=True)
    sid = str(spec.get("source_id") or "draft").strip()
    path = out_dir / f"{sid}.json"
    path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def render_adapter_stub(spec: dict) -> str:
    """Черновик Python-адаптера для ручной доработки (OSM-06)."""
    sid = spec.get("source_id", "new_source")
    name = spec.get("name", sid)
    base = spec.get("base_url", "")
    search = spec.get("search_url", base)
    return f'''"""Черновик адаптера: {name} — сгенерирован Source Scout, проверьте вручную."""

from tender_agents.models import SearchResultItem
from tender_agents.sources.base import SourceAdapter


class {sid.title().replace("_", "")}Adapter(SourceAdapter):
    source_id = "{sid}"

    def build_search_url(self, keyword: str) -> str:
        return "{search}".replace("{{keyword}}", keyword)

    async def search(self, keyword: str, **kwargs) -> list[SearchResultItem]:
        # TODO: нативный парсер или backend.extract_list
        return await super().search(keyword, **kwargs)
'''
