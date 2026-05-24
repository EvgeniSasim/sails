#!/usr/bin/env python3
"""Create Jules sessions from prompts/jules-task-*.md (order by filename)."""

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


def main() -> None:
    order = [
        "jules-task-zakupki-resilience.md",
        "jules-task-research-captcha-compliance.md",
        "jules-task-excel-import.md",
    ]
    by_name = {p.name: p for p in PROMPTS_DIR.glob("jules-task-*.md")}
    tasks = [by_name[n] for n in order if n in by_name]
    if not tasks:
        raise SystemExit("No jules-task-*.md in prompts/")
    branches = {
        "zakupki": "jules/zakupki-resilience",
        "research": "jules/research-captcha-compliance",
        "excel": "feature/excel-import-contacts",
    }
    for path in tasks:
        name = path.stem.replace("jules-task-", "")
        branch = branches.get(name.split("-")[0], f"jules/{name}")
        if "excel" in name:
            branch = "feature/excel-import-contacts"
        elif "research" in name:
            branch = "jules/research-captcha-compliance"
        elif "zakupki" in name:
            branch = "jules/zakupki-resilience"
        prompt = extract_prompt(path)
        title = f"tender-leads: {name[:60]}"
        print(f"Creating session: {path.name} → {branch} …", flush=True)
        out = create_session(title=title, prompt=prompt, branch_hint=branch)
        sid = out.get("id") or (out.get("name") or "").split("/")[-1]
        print(f"  OK session id={sid} name={out.get('name', '')}", flush=True)


if __name__ == "__main__":
    main()
