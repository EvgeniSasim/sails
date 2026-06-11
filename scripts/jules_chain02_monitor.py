#!/usr/bin/env python3
"""Poll Jules task02: resume → merge → pytest → launch next."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMPTS_DIR = ROOT / "prompts"
TRACKER = ROOT / "docs/jules-sessions-task02.md"
API = "https://jules.googleapis.com/v1alpha/sessions"
SOURCE = os.environ.get("JULES_SOURCE", "sources/github/EvgeniSasim/sails")
MAIN = os.environ.get("JULES_BRANCH", "main")
POLL_SEC = int(os.environ.get("JULES_POLL_SEC", "90"))
MAX_WAIT_PER_TASK = int(os.environ.get("JULES_MAX_WAIT_SEC", str(6 * 3600)))

TASKS = [
    ("10", "jules-task-10-extraction-hardening.md", "jules/task02-10-extraction"),
    ("11", "jules-task-11-offline-fixtures.md", "jules/task02-11-fixtures"),
    ("12", "jules-task-12-period-filter-ui.md", "jules/task02-12-period"),
    ("13", "jules-task-13-collect-report.md", "jules/task02-13-report"),
    ("14", "jules-task-14-resilience.md", "jules/task02-14-resilience"),
    ("15", "jules-task-15-export-csv.md", "jules/task02-15-export"),
    ("16", "jules-task-16-zakupki-adapter.md", "jules/task02-16-zakupki"),
    ("17", "jules-task-17-llm-fallback.md", "jules/task02-17-llm"),
]

PROMPT_NAMES = {
    "10": "jules-task-10-extraction-hardening",
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
    run(["git", "fetch", "origin"], check=False)


def remote_branches() -> list[str]:
    out = run(["git", "branch", "-r"], check=False).stdout
    return [
        ln.strip().replace("origin/", "")
        for ln in out.splitlines()
        if ln.strip().startswith("origin/") and "HEAD" not in ln
    ]


def find_branch(prefix: str) -> str | None:
    matches = sorted(b for b in remote_branches() if b.startswith(prefix))
    return matches[-1] if matches else None


def branch_merged_into_main(branch: str) -> bool:
    cp = run(["git", "branch", "-r", "--merged", f"origin/{MAIN}"], check=False)
    return branch in cp.stdout


def wait_branch(prefix: str) -> str | None:
    deadline = time.time() + MAX_WAIT_PER_TASK
    while time.time() < deadline:
        git_fetch()
        branch = find_branch(prefix)
        if branch:
            if branch_merged_into_main(branch):
                log(f"Branch {branch} already merged while waiting")
                return branch
            time.sleep(15)
            git_fetch()
            return find_branch(prefix) or branch
        log(f"Waiting {prefix}* … ({int(deadline - time.time())}s left)")
        time.sleep(POLL_SEC)
    return None


def merge_branch(branch: str) -> bool:
    run(["git", "checkout", "main"], check=False)
    run(["git", "pull", "origin", "main"], check=False)
    if branch_merged_into_main(branch):
        log(f"Already merged: {branch}")
        return True
    stat = run(["git", "diff", f"origin/{MAIN}...origin/{branch}", "--stat"], check=False)
    log(stat.stdout.strip())
    cp = run(["git", "merge", f"origin/{branch}", "-m", f"Merge Jules {branch}."], check=False)
    if cp.returncode != 0:
        log(f"MERGE FAIL: {cp.stderr}")
        return False
    run(["git", "push", "origin", "main"], check=False)
    return True


def pytest_offline() -> bool:
    py = ROOT / ".venv/bin/pytest"
    cmd = (
        [str(py), "tests/", "-q", "-m", "not network"]
        if py.exists()
        else ["pytest", "tests/", "-q", "-m", "not network"]
    )
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


def jules_create(prompt_file: str, branch_hint: str, *, retries: int = 5) -> str:
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
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                API,
                data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json", "x-goog-api-key": key},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                out = json.loads(resp.read().decode())
            return str(out.get("name", out.get("id", ""))).replace("sessions/", "")
        except urllib.error.HTTPError as e:
            body_text = e.read().decode() if e.fp else ""
            last_err = e
            log(f"Jules API attempt {attempt}/{retries} failed: HTTP {e.code} {body_text}")
            if attempt < retries:
                time.sleep(60 * attempt)
        except Exception as e:
            last_err = e
            log(f"Jules API attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                time.sleep(60 * attempt)
    raise last_err or RuntimeError("jules_create failed")


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


def tracker_status(num: str) -> str:
    for line in TRACKER.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"| {num} |"):
            return line.split("|")[-2].strip()
    return ""


def merge_and_test(num: str, branch: str) -> bool:
    log(f"Review {num}:\n{run(['git', 'diff', f'origin/{MAIN}...origin/{branch}', '--stat'], check=False).stdout.strip()}")
    if not merge_branch(branch):
        return False
    if not pytest_offline():
        log(f"STOP: task {num} merged but pytest failed — fix manually")
        return False
    patch_tracker(num, "done", branch, "влито")
    log(f"Task {num} OK")
    return True


def ensure_session(num: str, prompt_file: str, prefix: str) -> None:
    status = tracker_status(num)
    if status.startswith("ожидает") or not status:
        sid = jules_create(prompt_file, prefix)
        patch_tracker(num, sid, f"{prefix}-{sid}", "в работе")
        log(f"Launched task {num} session {sid}")


def main() -> int:
    if not os.environ.get("JULES_API_KEY"):
        log("JULES_API_KEY missing")
        return 1

    start = os.environ.get("JULES_START")
    log(f"Chain02 monitor start={start or 'auto'}")

    for num, prompt_file, prefix in TASKS:
        if start and num < start:
            continue

        status = tracker_status(num)
        if "влито" in status:
            log(f"Skip task {num} (already merged)")
            continue

        git_fetch()
        branch = find_branch(prefix)

        if branch and branch_merged_into_main(branch):
            patch_tracker(num, "done", branch, "влито")
            log(f"Task {num} was merged externally")
            continue

        if branch:
            if not merge_and_test(num, branch):
                return 1
            continue

        # No branch yet — launch session if needed, then wait
        if "в работе" not in status:
            try:
                ensure_session(num, prompt_file, prefix)
            except Exception as e:
                log(f"Cannot launch task {num} yet: {e}. Retry in {POLL_SEC}s")
                time.sleep(POLL_SEC)
                branch = wait_branch(prefix)
                if branch and not branch_merged_into_main(branch):
                    if not merge_and_test(num, branch):
                        return 1
                continue

        branch = wait_branch(prefix)
        if not branch:
            log(f"TIMEOUT task {num}")
            return 1
        if branch_merged_into_main(branch):
            patch_tracker(num, "done", branch, "влито")
            continue
        if not merge_and_test(num, branch):
            return 1

    log("=== Chain 02 complete ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
