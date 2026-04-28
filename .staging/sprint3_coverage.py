"""Sprint 3 / Wave A — coverage push from 10% to 25%.

Creates branch sprint-3/coverage-push, uploads three new test files for
persona_manager, answer_strategies and consistency_validator, leaves the
ratchet at the current 10% (we let CI report the new measurement, then
bump to 25 via a follow-up only when CI confirms it really is >= 25%).
"""

from __future__ import annotations

import base64
import json
import os
import sys
import time
import urllib.request
import urllib.error

TOKEN = os.environ["GH_TOKEN"]
REPO = "SIN-CLIs/playstealth-cli"
BRANCH = "sprint-3/coverage-push"
BASE = "main"
STAGING = "/vercel/share/v0-project/.staging"


def api(method: str, path: str, body: dict | None = None, raw: bool = False):
    url = f"https://api.github.com{path}"
    data = json.dumps(body).encode() if body else None
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.raw" if raw else "application/vnd.github+json",
    }
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        r = urllib.request.urlopen(req).read()
        return r.decode() if raw else (json.loads(r) if r else {})
    except urllib.error.HTTPError as e:
        return {"err": e.code, "msg": e.read().decode()[:400]}


def ensure_branch():
    main = api("GET", f"/repos/{REPO}/git/ref/heads/{BASE}")
    sha = main["object"]["sha"]
    print(f"main sha = {sha[:10]}")
    r = api("POST", f"/repos/{REPO}/git/refs", {"ref": f"refs/heads/{BRANCH}", "sha": sha})
    if r.get("err") == 422:
        print(f"branch {BRANCH} already exists, reusing")
    else:
        print(f"branch {BRANCH} created from main")


def put_file(path_in_repo: str, local_file: str, message: str):
    with open(local_file, "rb") as f:
        content = f.read()
    b64 = base64.b64encode(content).decode()
    existing = api("GET", f"/repos/{REPO}/contents/{path_in_repo}?ref={BRANCH}")
    body = {"message": message, "content": b64, "branch": BRANCH}
    if isinstance(existing, dict) and "sha" in existing:
        body["sha"] = existing["sha"]
        print(f"  updating {path_in_repo} (sha={existing['sha'][:10]})")
    else:
        print(f"  creating {path_in_repo}")
    r = api("PUT", f"/repos/{REPO}/contents/{path_in_repo}", body)
    if "commit" in r:
        print(f"    commit {r['commit']['sha'][:10]}")
    else:
        print(f"    ERROR {r}")
        return False
    return True


def open_pr() -> int:
    body = {
        "title": "test(coverage): unit tests for persona_manager, answer_strategies, consistency_validator",
        "head": BRANCH,
        "base": BASE,
        "body": (
            "## Sprint 3 / Wave A — Coverage Push\n\n"
            "Adds 39 unit tests across three previously-zero-coverage modules.\n\n"
            "### Test files added\n"
            "- `tests/test_persona_manager.py` — 13 tests (load/save round-trip, defaults, screening determinism)\n"
            "- `tests/test_answer_strategies.py` — 15 tests (Random/Consistent/Persona, heuristic matcher, factory)\n"
            "- `tests/test_consistency_validator.py` — 11 tests (record/load, contradictions, straight-lining, history trim)\n\n"
            "### Coverage expectation\n"
            "All three modules are pure stdlib (no Playwright, no network). They\n"
            "should reach 75-90% coverage individually, lifting the project\n"
            "average from ~11% to roughly 25%. The ratchet stays at 10% in this\n"
            "PR — we bump it to 25% in a follow-up commit only after CI confirms\n"
            "the new measurement.\n\n"
            "### Closes / refs\n"
            "- Refs #31 (Coverage-Reporting + ≥75% Gate, ratchet step 2)\n\n"
            "— v0 (CEO audit, Sprint 3)"
        ),
    }
    pr = api("POST", f"/repos/{REPO}/pulls", body)
    if "number" in pr:
        print(f"PR #{pr['number']} opened")
        return pr["number"]
    print(f"PR open failed: {pr}")
    return 0


def wait_for_checks(pr_num: int, timeout_s: int = 480) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        pr = api("GET", f"/repos/{REPO}/pulls/{pr_num}")
        sha = pr["head"]["sha"]
        cs = api("GET", f"/repos/{REPO}/commits/{sha}/check-runs")
        runs = cs.get("check_runs", [])
        if not runs:
            print("  (no checks yet)")
            time.sleep(10)
            continue
        green = sum(1 for c in runs if c.get("conclusion") in ("success", "skipped"))
        red = sum(1 for c in runs if c.get("conclusion") == "failure")
        running = sum(1 for c in runs if c["status"] != "completed")
        print(f"  green={green} red={red} running={running}")
        if running == 0:
            return red == 0
        time.sleep(20)
    print("  TIMEOUT waiting for checks")
    return False


def merge_pr(pr_num: int):
    pr = api("GET", f"/repos/{REPO}/pulls/{pr_num}")
    r = api(
        "PUT",
        f"/repos/{REPO}/pulls/{pr_num}/merge",
        {"merge_method": "squash", "commit_title": pr["title"] + f" (#{pr_num})"},
    )
    if r.get("merged"):
        print(f"  PR #{pr_num} MERGED")
        return True
    print(f"  merge failed: {r}")
    return False


def main():
    print(f"=== Sprint 3 / Wave A ({REPO}) ===")
    ensure_branch()

    files = [
        ("tests/test_persona_manager.py", f"{STAGING}/tests/test_persona_manager.py"),
        ("tests/test_answer_strategies.py", f"{STAGING}/tests/test_answer_strategies.py"),
        ("tests/test_consistency_validator.py", f"{STAGING}/tests/test_consistency_validator.py"),
    ]
    for repo_path, local_path in files:
        msg = f"test: add {os.path.basename(repo_path)} (Sprint 3 coverage push)"
        if not put_file(repo_path, local_path, msg):
            sys.exit(1)

    pr_num = open_pr()
    if not pr_num:
        sys.exit(1)
    print("\n--- waiting for CI ---")
    ok = wait_for_checks(pr_num)
    if not ok:
        print("CI red — leaving PR open for inspection")
        sys.exit(2)
    print("\n--- merging ---")
    merge_pr(pr_num)


if __name__ == "__main__":
    main()
