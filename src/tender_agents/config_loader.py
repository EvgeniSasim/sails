from pathlib import Path

import yaml

from tender_agents.settings import CONFIG_DIR

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


def load_sources() -> dict[str, dict]:
    path = CONFIG_DIR / "sources.yaml"
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    sources = data.get("sources", {})
    return {k: v for k, v in sources.items() if v.get("enabled", True)}
