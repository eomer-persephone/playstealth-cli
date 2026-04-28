"""Triage open Dependabot PRs in both repos.

Safe (CI tooling, types-group): approve + enable auto-merge once CI is green.
Risky (library major bumps): post migration-notes comment, label, do NOT merge.
"""
from __future__ import annotations
import json
import os
import time
import urllib.error
import urllib.request

TOKEN = os.environ["GH_TOKEN"]
HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github+json",
    "User-Agent": "v0-sprint2-triage",
}


def api(method: str, path: str, body=None):
    url = f"https://api.github.com{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=HEADERS)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


SAFE = {
    "SIN-CLIs/playstealth-cli": [52, 53],
    "SIN-CLIs/unmask-cli": [61, 62, 63, 64, 65, 66],
}

# (number, lib, migration_notes)
RISKY = {
    "SIN-CLIs/unmask-cli": [
        (
            67, "vitest 2 -> 4",
            "Skipped major version 3. Breaking changes:\n"
            "- `vi.mocked()` strict typing changes\n"
            "- workspace config moved to `vitest.workspace.ts`\n"
            "- removed deprecated `inline` deps option\n\n"
            "Migration: https://vitest.dev/guide/migration\n"
            "Action: bump to v3 first, run tests, then v4. Do not skip versions."
        ),
        (
            68, "zod 3 -> 4",
            "Major rewrite with breaking changes:\n"
            "- `.parse()` return type tightened\n"
            "- error format changed (`.issues` shape)\n"
            "- `z.string().uuid()` becomes `z.uuid()`\n"
            "- `z.record()` requires explicit key type\n\n"
            "Migration: https://zod.dev/v4 + run codemod `npx zod-codemod`.\n"
            "Action: hold until consumer code audit complete."
        ),
        (
            69, "typescript 5 -> 6",
            "TypeScript 6.0 just released. Breaking changes still being documented.\n"
            "Action: hold for at least 2-4 weeks until ecosystem catches up.\n"
            "Major risks: stricter inference, new lib.d.ts, deprecation removals."
        ),
        (
            70, "commander 12 -> 14",
            "Skipped major version 13. Breaking changes:\n"
            "- ESM-only (no more CommonJS)\n"
            "- Node 20+ required\n"
            "- some option-parsing edge cases changed\n\n"
            "Migration: https://github.com/tj/commander.js/releases\n"
            "Action: verify ESM compatibility of consumers first."
        ),
        (
            71, "eslint 9 -> 10",
            "ESLint 10 just released, flat-config now mandatory.\n"
            "Breaking changes:\n"
            "- `.eslintrc.*` no longer supported\n"
            "- some rules renamed/moved\n"
            "- plugin API changes\n\n"
            "Migration: https://eslint.org/docs/latest/use/migrate-to-10\n"
            "Action: ensure flat-config is in place, then update plugins in lockstep."
        ),
    ]
}


def approve(repo: str, pr: int) -> None:
    status, data = api("POST", f"/repos/{repo}/pulls/{pr}/reviews", {
        "event": "APPROVE",
        "body": "Auto-approved by CEO oversight: safe CI/tooling major bump (no runtime impact). "
                "Will auto-merge once required checks pass.",
    })
    print(f"  approve #{pr} -> HTTP {status}")


def enable_automerge(repo: str, pr: int) -> None:
    # GraphQL API needed for enablePullRequestAutoMerge
    _, pr_data = api("GET", f"/repos/{repo}/pulls/{pr}")
    node_id = pr_data.get("node_id")
    if not node_id:
        print(f"  automerge #{pr} -> no node_id")
        return
    query = {
        "query": (
            "mutation($id:ID!) { enablePullRequestAutoMerge("
            "input:{pullRequestId:$id, mergeMethod:SQUASH}) "
            "{ pullRequest { number autoMergeRequest { enabledAt } } } }"
        ),
        "variables": {"id": node_id},
    }
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps(query).encode(),
        method="POST",
        headers=HEADERS,
    )
    try:
        with urllib.request.urlopen(req) as r:
            body = json.loads(r.read())
        if "errors" in body:
            print(f"  automerge #{pr} -> ERROR {body['errors'][0]['message'][:100]}")
        else:
            print(f"  automerge #{pr} -> ENABLED")
    except urllib.error.HTTPError as e:
        print(f"  automerge #{pr} -> HTTP {e.code} {e.read()[:200]}")


def comment_risky(repo: str, pr: int, lib: str, notes: str) -> None:
    body = (
        f"## Migration assessment for {lib}\n\n"
        f"{notes}\n\n"
        "---\n"
        "**Status:** parking this PR. Add label `deps-major-hold`. Will be revisited in a "
        "dedicated migration PR with full test coverage and consumer audit, "
        "not as an unattended Dependabot merge.\n\n"
        "_Auto-comment from Sprint 2 triage. Close & re-create only if you have a smoke-test plan._"
    )
    s, _ = api("POST", f"/repos/{repo}/issues/{pr}/comments", {"body": body})
    print(f"  comment #{pr} ({lib}) -> HTTP {s}")
    api("POST", f"/repos/{repo}/issues/{pr}/labels", {"labels": ["deps-major-hold"]})


def ensure_label(repo: str) -> None:
    api("POST", f"/repos/{repo}/labels", {
        "name": "deps-major-hold",
        "color": "d93f0b",
        "description": "Major-version dependency bump on hold pending migration plan.",
    })


def main() -> None:
    for repo in ("SIN-CLIs/playstealth-cli", "SIN-CLIs/unmask-cli"):
        ensure_label(repo)
    print("\n== Safe PRs: approve + auto-merge ==")
    for repo, prs in SAFE.items():
        print(f"-- {repo} --")
        for pr in prs:
            approve(repo, pr)
            enable_automerge(repo, pr)
            time.sleep(0.5)
    print("\n== Risky PRs: migration comment + label ==")
    for repo, items in RISKY.items():
        print(f"-- {repo} --")
        for pr, lib, notes in items:
            comment_risky(repo, pr, lib, notes)
            time.sleep(0.5)
    print("\nDone.")


if __name__ == "__main__":
    main()
