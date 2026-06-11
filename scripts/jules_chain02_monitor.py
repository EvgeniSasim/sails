#!/usr/bin/env python3
"""Poll Jules task02: wait branch → merge → pytest → launch next."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMPTS_DIR = ROOT / "prompts"
TRACKER = ROOT / "docs/jules-sessions-task02.md"
API = "https://jules.googleapis.com/v1alpha/sessions"
SOURCE = os.environ.get("JULES_SOURCE", "sources/github/EvgeniSasim/sails")
MAIN = os.environ.get("JULES_BRANCH", "main")
POLL_SEC = int(os.environ.get("JULES_POLL_SEC", "90"))
MAX_WAIT_PER_TASK = int(os.environ.get("JULES_MAX_WAIT_SEC", str(4 * 3600)))

TASKS = [
    ("11", "jules-task-11-offline-fixtures.md", "jules/task02-11-fixtures"),
    ("12", "jules-task-12-period-filter-ui.md", "jules/task02-12-period"),
    ("13", "jules-task-13-collect-report.md", "jules/task02-13-report"),
    ("14", "jules-task-14-resilience.md", "jules/task02-14-resilience"),
    ("15", "jules-task-15-export-csv.md", "jules/task02-15-export"),
    ("16", "jules-task-16-zakupki-adapter.md", "jules/task02-16-zakupki"),
    ("17", "jules-task-17-llm-fallback.md", "jules/task02-17-llm"),
]

PROMPT_NAMES = {
    "11": "jules-task-11-offline-fixtures",
    "12": "jules-task-12-period-filter-ui",
    "13": "jules-task-13-collect-report",
    "14": "jules-task-14-resilience",
    "15": "jules-task-15-export-csv",
    "16": "jules-task-16-zakupki-adapter",
    "17": "jules-task-17-llm-fallback",
}

LOG = ROOT / "data/debug/jules-chain02-monitor.log"


def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    log(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=check)


def git_fetch() -> None:
    run(["git", "fetch", "origin"])


def remote_branches() -> list[str]:
    out = run(["git", "branch", "-r"]).stdout
    return [
        ln.strip().replace("origin/", "")
        for ln in out.splitlines()
        if ln.strip().startswith("origin/") and "HEAD" not in ln
    ]


def find_branch(prefix: str) -> str | None:
    matches = sorted(b for b in remote_branches() if b.startswith(prefix))
    return matches[-1] if matches else None


def branch_merged_into_main(branch: str) -> bool:
    cp = run(["git", "branch", "-r", "--merged", "origin/main"], check=False)
    return branch in cp.stdout


def wait_branch(prefix: str) -> str | None:
    deadline = time.time() + MAX_WAIT_PER_TASK
    while time.time() < deadline:
        git_fetch()
        branch = find_branch(prefix)
        if branch and not branch_merged_into_main(branch):
            time.sleep(20)
            git_fetch()
            return find_branch(prefix) or branch
        if branch and branch_merged_into_main(branch):
            log(f"Branch {branch} already merged")
            return branch
        log(f"Waiting {prefix}* …")
        time.sleep(POLL_SEC)
    return None


def merge_branch(branch: str) -> bool:
    if branch_merged_into_main(branch):
        log(f"Skip merge, already in main: {branch}")
        run(["git", "checkout", "main"], check=False)
        run(["git", "pull", "origin", "main"], check=False)
        return True
    run(["git", "checkout", "main"])
    run(["git", "pull", "origin", "main"])
    stat = run(["git", "diff", f"origin/{MAIN}...origin/{branch}", "--stat"], check=False)
    log(stat.stdout)
    cp = run(["git", "merge", f"origin/{branch}", "-m", f"Merge Jules {branch}."], check=False)
    if cp.returncode != 0:
        log(f"MERGE FAIL: {cp.stderr}")
        return False
    run(["git", "push", "origin", "main"])
    return True


def pytest_offline() -> bool:
    py = ROOT / ".venv/bin/pytest"
    cmd = [str(py), "tests/", "-q", "-m", "not network"] if py.exists() else ["pytest", "tests/", "-q", "-m", "not network"]
    cp = run(cmd, check=False)
    if cp.returncode != 0:
        log(f"PYTEST FAIL:\n{cp.stdout}\n{cp.stderr}")
        return False
    log(cp.stdout.strip())
    return True


def extract_prompt(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    m = re.search(r"```markdown\s*\n(.*?)```", text, re.DOTALL)
    if not m:
        raise ValueError(path)
    return m.group(1).strip()


def jules_create(prompt_file: str, branch_hint: str) -> str:
    key = os.environ["JULES_API_KEY"]
    prompt = extract_prompt(PROMPTS_DIR / prompt_file)
    name = prompt_file.replace(".md", "")
    body = {
        "title": f"tender-leads task02: {name[:45]}",
        "prompt": f"{prompt}\n\nTarget git branch for PR: `{branch_hint}`.",
        "sourceContext": {
            "source": SOURCE,
            "githubRepoContext": {"startingBranch": MAIN},
        },
        "automationMode": "AUTO_CREATE_PR",
    }
    req = urllib.request.Request(
        API,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        out = json.loads(resp.read().decode())
    sid = str(out.get("name", out.get("id", ""))).replace("sessions/", "")
    return sid


def patch_tracker(num: str, session_id: str, pr_branch: str, status: str) -> None:
    lines = TRACKER.read_text(encoding="utf-8").splitlines()
    fname = PROMPT_NAMES[num]
    for i, line in enumerate(lines):
        if line.startswith(f"| {num} |"):
            lines[i] = f"| {num} | {fname} | `{session_id}` | `{pr_branch}` | {status} |"
            break
    TRACKER.write_text("\n".join(lines) + "\n", encoding="utf-8")
    run(["git", "add", str(TRACKER)], check=False)
    run(["git", "commit", "-m", f"Jules task02-{num}: {status}."], check=False)
    run(["git", "push", "origin", "main"], check=False)


def review_notes(num: str, branch: str) -> str:
    diff = run(["git", "diff", f"origin/{MAIN}...origin/{branch}", "--stat"], check=False).stdout
    return diff.strip()


def process_task(num: str, prompt_file: str, prefix: str, *, launch_if_missing: bool) -> bool:
    log(f"=== Task {num} ===")
    branch = wait_branch(prefix)
    if not branch:
        log(f"TIMEOUT task {num}")
        return False

    notes = review_notes(num, branch)
    log(f"Review {num}:\n{notes}")

    if not merge_branch(branch):
        return False
    if not pytest_offline():
        return False

    patch_tracker(num, "done", branch, "влито")
    log(f"Task {num} OK")
    return True


def main() -> int:
    if not os.environ.get("JULES_API_KEY"):
        log("JULES_API_KEY missing")
        return 1

    start = os.environ.get("JULES_START", "11")
    log(f"Chain02 monitor from task {start}")

    for i, (num, prompt_file, prefix) in enumerate(TASKS):
        if num < start:
            continue

        if num == start:
            # task 11 already has session; just wait
            if not process_task(num, prompt_file, prefix, launch_if_missing=False):
                return 1
        else:
            sid = jules_create(prompt_file, prefix)
            actual_branch = f"{prefix}-{sid}"
            patch_tracker(num, sid, actual_branch, "в работе")
            log(f"Started task {num} session {sid}")
            if not process_task(num, prompt_file, prefix, launch_if_missing=False):
                return 1

    log("=== Chain 02 complete ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
