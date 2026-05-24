import json
import logging
from pathlib import Path

import yaml

from tender_agents.settings import CONFIG_DIR

logger = logging.getLogger(__name__)

_EXTRA_KEYWORD_FILES = ("keywords_hr.yaml", "keywords_cx.yaml")


def _load_yaml_keywords(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return [str(k).strip() for k in data.get("keywords", []) if str(k).strip()]


def load_keywords_raw() -> dict:
    path = CONFIG_DIR / "keywords.yaml"
    if not path.exists():
        return {"keywords": [], "merge_extra": False}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_keywords(*, merge_extra: bool | None = None) -> list[str]:
    """
    Ключи для SearchAgent.

    По умолчанию — только список из «Настройки → Ключи» (keywords.yaml).
    Файлы keywords_hr.yaml / keywords_cx.yaml подключаются только при merge_extra: true.
    """
    data = load_keywords_raw()
    keywords: list[str] = [
        str(k).strip() for k in data.get("keywords", []) if str(k).strip()
    ]
    use_extra = data.get("merge_extra", False) if merge_extra is None else merge_extra
    if use_extra:
        for name in _EXTRA_KEYWORD_FILES:
            keywords.extend(_load_yaml_keywords(CONFIG_DIR / name))
    return list(dict.fromkeys(keywords))


def describe_keywords_setup() -> dict:
    """Для UI: что реально уйдёт в сбор."""
    data = load_keywords_raw()
    main = [str(k).strip() for k in data.get("keywords", []) if str(k).strip()]
    merge_extra = bool(data.get("merge_extra", False))
    extra: list[str] = []
    if merge_extra:
        for name in _EXTRA_KEYWORD_FILES:
            extra.extend(_load_yaml_keywords(CONFIG_DIR / name))
    effective = list(dict.fromkeys(main + extra))
    return {
        "main": main,
        "extra": list(dict.fromkeys(extra)),
        "merge_extra": merge_extra,
        "effective": effective,
    }


def _merge_sources_drafts(sources: dict[str, dict]) -> None:
    """Черновики адаптеров из config/sources.d/*.json (по умолчанию disabled)."""
    draft_dir = CONFIG_DIR / "sources.d"
    if not draft_dir.is_dir():
        return
    for path in sorted(draft_dir.glob("*.json")):
        try:
            with path.open(encoding="utf-8") as f:
                spec = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("sources.d: пропуск %s: %s", path.name, e)
            continue
        if not isinstance(spec, dict):
            logger.warning("sources.d: %s — ожидается JSON-объект", path.name)
            continue
        sid = str(spec.get("id") or path.stem).strip()
        if not sid or sid in sources:
            continue
        entry = {k: v for k, v in spec.items() if k != "id"}
        entry.setdefault("enabled", False)
        entry["_draft_from"] = path.name
        sources[sid] = entry


def load_sources() -> dict[str, dict]:
    path = CONFIG_DIR / "sources.yaml"
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    sources: dict[str, dict] = dict(data.get("sources", {}))
    _merge_sources_drafts(sources)
    return {k: v for k, v in sources.items() if v.get("enabled", True)}
