#!/usr/bin/env python3
"""Create Jules sessions from prompts/jules-task-*.md (ordered chains 01 / 02)."""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMPTS_DIR = ROOT / "prompts"
API = "https://jules.googleapis.com/v1alpha/sessions"
SOURCE = os.environ.get("JULES_SOURCE", "sources/github/EvgeniSasim/sails")
BRANCH = os.environ.get("JULES_BRANCH", "main")

TASK01_ORDER = [
    "jules-task-01-collect-cli.md",
    "jules-task-02-browser-session.md",
    "jules-task-03-sberbank-search.md",
    "jules-task-04-sberbank-pagination.md",
    "jules-task-05-sberbank-detail.md",
    "jules-task-06-orchestrator.md",
    "jules-task-07-jsonl-store.md",
    "jules-task-08-sqlite-list.md",
    "jules-task-09-observability.md",
]

TASK02_ORDER = [
    "jules-task-10-extraction-hardening.md",
    "jules-task-11-offline-fixtures.md",
    "jules-task-12-period-filter-ui.md",
    "jules-task-13-collect-report.md",
    "jules-task-14-resilience.md",
    "jules-task-15-export-csv.md",
    "jules-task-16-zakupki-adapter.md",
    "jules-task-17-llm-fallback.md",
]

TASK01_BRANCHES = {
    "jules-task-01-collect-cli.md": "jules/task01-01-collect-cli",
    "jules-task-02-browser-session.md": "jules/task01-02-browser",
    "jules-task-03-sberbank-search.md": "jules/task01-03-sber-search",
    "jules-task-04-sberbank-pagination.md": "jules/task01-04-pagination",
    "jules-task-05-sberbank-detail.md": "jules/task01-05-detail",
    "jules-task-06-orchestrator.md": "jules/task01-06-orchestrator",
    "jules-task-07-jsonl-store.md": "jules/task01-07-jsonl",
    "jules-task-08-sqlite-list.md": "jules/task01-08-sqlite",
    "jules-task-09-observability.md": "jules/task01-09-observability",
}

TASK02_BRANCHES = {
    "jules-task-10-extraction-hardening.md": "jules/task02-10-extraction",
    "jules-task-11-offline-fixtures.md": "jules/task02-11-fixtures",
    "jules-task-12-period-filter-ui.md": "jules/task02-12-period",
    "jules-task-13-collect-report.md": "jules/task02-13-report",
    "jules-task-14-resilience.md": "jules/task02-14-resilience",
    "jules-task-15-export-csv.md": "jules/task02-15-export",
    "jules-task-16-zakupki-adapter.md": "jules/task02-16-zakupki",
    "jules-task-17-llm-fallback.md": "jules/task02-17-llm",
}

ALL_BRANCHES = {**TASK01_BRANCHES, **TASK02_BRANCHES}


def extract_prompt(md_path: Path) -> str:
    text = md_path.read_text(encoding="utf-8")
    m = re.search(r"```markdown\s*\n(.*?)```", text, re.DOTALL)
    if not m:
        raise ValueError(f"No ```markdown block in {md_path}")
    return m.group(1).strip()


def create_session(*, title: str, prompt: str, branch_hint: str) -> dict:
    key = os.environ.get("JULES_API_KEY")
    if not key:
        raise SystemExit("JULES_API_KEY not set")
    body = {
        "title": title,
        "prompt": f"{prompt}\n\nTarget git branch for PR: `{branch_hint}`.",
        "sourceContext": {
            "source": SOURCE,
            "githubRepoContext": {"startingBranch": BRANCH},
        },
        "automationMode": "AUTO_CREATE_PR",
    }
    req = urllib.request.Request(
        API,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": key,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def resolve_tasks() -> list[Path]:
    single = os.environ.get("JULES_TASK", "").strip()
    if single:
        path = PROMPTS_DIR / single if not single.startswith("prompts/") else ROOT / single
        if not path.is_file():
            raise SystemExit(f"JULES_TASK not found: {path}")
        return [path]
    if os.environ.get("JULES_TASK02") == "1":
        return [PROMPTS_DIR / n for n in TASK02_ORDER if (PROMPTS_DIR / n).is_file()]
    if os.environ.get("JULES_TASK01") == "1":
        by_name = {p.name: p for p in PROMPTS_DIR.glob("jules-task-01-*.md")}
        return [by_name[n] for n in TASK01_ORDER if n in by_name]
    raise SystemExit(
        "Set JULES_TASK=prompts/…md or JULES_TASK01=1 or JULES_TASK02=1"
    )


def session_title(path: Path) -> str:
    name = path.stem.replace("jules-task-", "")
    if name.startswith("0") and len(name) >= 2 and name[1].isdigit():
        return f"tender-leads task01: {name[:50]}"
    if name[0:2].isdigit():
        return f"tender-leads task02: {name[:50]}"
    return f"tender-leads: {name[:50]}"


def main() -> None:
    tasks = resolve_tasks()
    for path in tasks:
        branch = ALL_BRANCHES.get(path.name, f"jules/{path.stem}")
        prompt = extract_prompt(path)
        title = session_title(path)
        print(f"Creating session: {path.name} → {branch} …", flush=True)
        try:
            out = create_session(title=title, prompt=prompt, branch_hint=branch)
        except urllib.error.HTTPError as e:
            body = e.read().decode() if e.fp else ""
            print(f"HTTP {e.code}: {body}", file=sys.stderr)
            raise SystemExit(1) from e
        sid = out.get("name", out.get("id", out))
        print(f"  OK: {sid}", flush=True)


if __name__ == "__main__":
    main()
