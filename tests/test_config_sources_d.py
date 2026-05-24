"""config/sources.d merge in load_sources()."""

import json

from tender_agents.config_loader import load_sources


def test_load_sources_merges_sources_d_enabled(tmp_path, monkeypatch):
    draft_dir = tmp_path / "sources.d"
    draft_dir.mkdir()
    (draft_dir / "draft_site.json").write_text(
        json.dumps(
            {
                "id": "draft_site",
                "name": "Draft",
                "base_url": "https://example.com",
                "search_url": "https://example.com/search",
                "enabled": True,
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "sources.yaml").write_text(
        "sources:\n  zakupki:\n    enabled: true\n    name: EIS\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("tender_agents.config_loader.CONFIG_DIR", tmp_path)
    sources = load_sources()
    assert "zakupki" in sources
    assert "draft_site" in sources
    assert sources["draft_site"]["name"] == "Draft"


def test_load_sources_skips_disabled_draft(tmp_path, monkeypatch):
    draft_dir = tmp_path / "sources.d"
    draft_dir.mkdir()
    (draft_dir / "off.json").write_text(
        json.dumps({"name": "Off", "base_url": "https://x.ru", "enabled": False}),
        encoding="utf-8",
    )
    (tmp_path / "sources.yaml").write_text("sources: {}\n", encoding="utf-8")
    monkeypatch.setattr("tender_agents.config_loader.CONFIG_DIR", tmp_path)
    assert "off" not in load_sources()
