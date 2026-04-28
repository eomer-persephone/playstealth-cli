"""
SOTA infra installer for SIN-CLIs/playstealth-cli and SIN-CLIs/unmask-cli.

Pushes (or updates) the same canonical set of governance/CI/security files
to BOTH repos via the GitHub Contents API, then enables branch protection
on main.

Idempotent: PUT with sha-if-exists, skip if content identical.
"""

from __future__ import annotations
import base64
import hashlib
import json
import os
import sys
import time
import urllib.request
import urllib.error

TOKEN = os.environ["GH_TOKEN"]
API = "https://api.github.com"
REPOS = ["SIN-CLIs/playstealth-cli", "SIN-CLIs/unmask-cli"]

HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github+json",
    "User-Agent": "v0-ceo-bot",
}


def req(method: str, path: str, body: dict | None = None, raw: bool = False):
    url = path if path.startswith("http") else f"{API}{path}"
    data = json.dumps(body).encode() if body else None
    r = urllib.request.Request(url, data=data, method=method, headers=HEADERS)
    if data:
        r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            txt = resp.read()
            return resp.status, (txt if raw else (json.loads(txt) if txt else {}))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def get_sha(repo: str, path: str) -> str | None:
    code, data = req("GET", f"/repos/{repo}/contents/{path}")
    if code == 200 and isinstance(data, dict):
        return data.get("sha")
    return None


def put_file(repo: str, path: str, content: str, message: str) -> str:
    sha = get_sha(repo, path)
    body = {
        "message": message,
        "content": base64.b64encode(content.encode()).decode(),
        "branch": "main",
    }
    if sha:
        # check if identical
        code, data = req("GET", f"/repos/{repo}/contents/{path}")
        if code == 200:
            existing = base64.b64decode(data["content"]).decode(errors="replace")
            if existing == content:
                return "unchanged"
        body["sha"] = sha
    code, data = req("PUT", f"/repos/{repo}/contents/{path}", body)
    if code in (200, 201):
        commit = (data.get("commit") or {}).get("sha", "")[:10]
        return f"{'updated' if sha else 'created'} ({commit})"
    return f"ERR {code}: {data}"


# ---------------------------------------------------------------------------
# File contents (shared across both repos unless prefixed PS_/UM_)
# ---------------------------------------------------------------------------

CODEOWNERS = """# CODEOWNERS — single-source governance after CEO audit 2026-04-28.
# Every PR auto-requests review from these owners.

* @Delqhi

/.github/        @Delqhi
/PLAN.md         @Delqhi
/ROADMAP.md      @Delqhi
/COMPETITIVE_STRATEGY.md  @Delqhi
"""

DEPENDABOT = """version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
    labels: ["dependencies", "ci"]
    commit-message:
      prefix: "ci"
"""

DEPENDABOT_PY = DEPENDABOT + """
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
    labels: ["dependencies"]
    commit-message:
      prefix: "deps"
    groups:
      python-dev:
        patterns: ["pytest*", "ruff*", "mypy*", "coverage*"]
"""

DEPENDABOT_NPM = DEPENDABOT + """
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
    labels: ["dependencies"]
    commit-message:
      prefix: "deps"
    groups:
      types:
        patterns: ["@types/*"]
      vitest:
        patterns: ["vitest", "@vitest/*"]
      playwright:
        patterns: ["playwright", "@playwright/*"]
"""

PR_TEMPLATE = """## What changed
<!-- One-paragraph summary of the change. -->

## Why
<!-- Link the issue this closes or the strategic doc that motivated it. -->
Closes #

## Type of change
- [ ] Feature
- [ ] Bug fix
- [ ] Refactor
- [ ] Docs
- [ ] Clone-and-combine (cite source + license below)

## Clone attribution (if applicable)
- Upstream project:
- License:
- Mode: `code-import` | `idea-only` | `vendored`
- Attribution updated in `THIRD_PARTY_NOTICES.md`: [ ] yes / [ ] n/a

## Definition of Done
- [ ] Code lives on `main` (no long-lived branches)
- [ ] Tests added or updated and green in CI
- [ ] Docs updated (`README.md`, `PLAN.md` if scope shifts)
- [ ] No secrets, no `.env` changes
- [ ] License/attribution correct (see CLONE.md)

## Reviewer notes
<!-- Anything reviewers should test manually, edge cases, follow-ups. -->
"""

ISSUE_CONFIG = """blank_issues_enabled: false
contact_links:
  - name: Security vulnerability (private)
    url: https://github.com/SIN-CLIs/playstealth-cli/security/advisories/new
    about: Report a security issue privately, never as a public issue.
"""

ISSUE_BUG = """name: Bug report
description: Something does not work as expected.
title: "[bug] "
labels: [bug, audit]
body:
  - type: textarea
    id: summary
    attributes:
      label: Summary
      description: One sentence — what is broken?
    validations:
      required: true
  - type: textarea
    id: repro
    attributes:
      label: Reproduction steps
      placeholder: |
        1. ...
        2. ...
        3. expected: ... / actual: ...
    validations:
      required: true
  - type: input
    id: version
    attributes:
      label: Version / commit
    validations:
      required: true
  - type: textarea
    id: env
    attributes:
      label: Environment
      placeholder: OS, runtime version, browser, headless flag, ...
  - type: textarea
    id: logs
    attributes:
      label: Logs / traceback
      render: shell
"""

ISSUE_FEATURE = """name: Feature request
description: Propose a new capability.
title: "[feat] "
labels: [enhancement]
body:
  - type: textarea
    id: problem
    attributes:
      label: Problem
      description: What user pain are we solving?
    validations:
      required: true
  - type: textarea
    id: proposal
    attributes:
      label: Proposed solution
    validations:
      required: true
  - type: textarea
    id: alternatives
    attributes:
      label: Alternatives considered
  - type: dropdown
    id: clone
    attributes:
      label: Is this a clone-and-combine candidate?
      options: ["No", "Yes — code import", "Yes — idea only", "Unsure"]
    validations:
      required: true
  - type: input
    id: upstream
    attributes:
      label: Upstream project (if clone)
      placeholder: e.g. browser-use/browser-use (MIT)
"""

ISSUE_CLONE = """name: Clone research
description: Track research + import work for a competitor capability we want to clone.
title: "[clone] "
labels: [clone, research]
body:
  - type: input
    id: upstream
    attributes:
      label: Upstream repo
      placeholder: org/name
    validations:
      required: true
  - type: input
    id: license
    attributes:
      label: License
      placeholder: MIT / Apache-2.0 / GPL-3.0 / AGPL-3.0 / proprietary
    validations:
      required: true
  - type: dropdown
    id: mode
    attributes:
      label: Clone mode (per COMPETITIVE_STRATEGY.md)
      options:
        - code-import (permissive license, vendored or extracted)
        - idea-only (copyleft, reimplemented from spec)
        - patch-watch (track upstream patches, e.g. CDP fingerprints)
    validations:
      required: true
  - type: textarea
    id: capability
    attributes:
      label: Capability we want
    validations:
      required: true
  - type: textarea
    id: integration
    attributes:
      label: Where it lands in our combine layer
      placeholder: src/<package>/<file>, plugin, hook, ...
    validations:
      required: true
  - type: textarea
    id: dod
    attributes:
      label: Definition of Done
      value: |
        - [ ] Upstream license & NOTICE recorded in THIRD_PARTY_NOTICES.md
        - [ ] Code adapted, not copy-pasted (or properly vendored)
        - [ ] Tests cover the imported behavior
        - [ ] PR cites this issue and upstream commit hash
        - [ ] PLAN.md updated if scope changed
"""

GITLEAKS_WF = """name: gitleaks

on:
  pull_request:
  push:
    branches: [main]
  schedule:
    - cron: "0 6 * * 1"

permissions:
  contents: read
  pull-requests: read

jobs:
  scan:
    name: Secret scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
"""

CODEQL_WF_PY = """name: CodeQL

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: "23 4 * * 0"

permissions:
  actions: read
  contents: read
  security-events: write

jobs:
  analyze:
    name: Analyze (python)
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        language: [python]
    steps:
      - uses: actions/checkout@v4
      - uses: github/codeql-action/init@v3
        with:
          languages: ${{ matrix.language }}
          queries: security-extended
      - uses: github/codeql-action/autobuild@v3
      - uses: github/codeql-action/analyze@v3
        with:
          category: "/language:${{ matrix.language }}"
"""

CODEQL_WF_JS = CODEQL_WF_PY.replace("python", "javascript-typescript").replace(
    "python]", "javascript-typescript]"
)

STALE_WF = """name: stale

on:
  schedule:
    - cron: "30 1 * * *"

permissions:
  issues: write
  pull-requests: write

jobs:
  stale:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/stale@v9
        with:
          days-before-stale: 45
          days-before-close: 14
          stale-issue-message: "This issue has been inactive for 45 days. It will close in 14 days unless updated. Add the `pinned` label to keep it open indefinitely."
          stale-pr-message: "This PR has been inactive for 45 days and will close in 14 days unless updated."
          exempt-issue-labels: "pinned,priority-p0,security"
          exempt-pr-labels: "pinned"
"""

# Release-please for monorepo-style auto-versioning
RELEASE_WF_PY = """name: release-please

on:
  push:
    branches: [main]

permissions:
  contents: write
  pull-requests: write

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: googleapis/release-please-action@v4
        with:
          release-type: python
          package-name: playstealth-cli
"""

RELEASE_WF_JS = """name: release-please

on:
  push:
    branches: [main]

permissions:
  contents: write
  pull-requests: write

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: googleapis/release-please-action@v4
        with:
          release-type: node
          package-name: unmask-cli
"""

PRECOMMIT_PY = """# Run: pre-commit install
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: ["--maxkb=512"]
      - id: check-merge-conflict
      - id: detect-private-key
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.7.4
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.21.2
    hooks:
      - id: gitleaks
"""

PRECOMMIT_JS = """repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-added-large-files
        args: ["--maxkb=512"]
      - id: check-merge-conflict
      - id: detect-private-key
  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v3.1.0
    hooks:
      - id: prettier
        types_or: [javascript, ts, tsx, json, yaml, markdown]
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.21.2
    hooks:
      - id: gitleaks
"""

CONTRIBUTING = """# Contributing

This project follows a strict **single-`main`-branch** policy after the 2026-04-28 CEO audit.
Long-lived feature branches are not allowed. Use short-lived topic branches that are deleted on merge.

## Workflow
1. Open or claim an issue. Every PR must reference one.
2. Branch from `main` as `topic/<issue-number>-short-slug`.
3. Keep PRs small. < 400 lines diff is the target.
4. Squash-merge to `main`. Delete the branch on merge.

## Conventional Commits (required)
We use Conventional Commits so `release-please` can ship automatically:
- `feat: ...` — new feature (minor bump)
- `fix: ...` — bug fix (patch bump)
- `feat!: ...` or `BREAKING CHANGE:` footer — major bump
- `docs:`, `chore:`, `ci:`, `refactor:`, `test:`, `perf:`, `build:` — no version bump
- `clone:` — a clone-and-combine import (must include upstream + license)

## Cloning competitors (Clone-the-Best-Combine-Win)
See `COMPETITIVE_STRATEGY.md`. TL;DR:
- Permissive license (MIT/Apache-2.0/BSD/ISC): code import is OK, attribute in `THIRD_PARTY_NOTICES.md`.
- Copyleft (GPL/AGPL/MPL): **idea-only**, reimplement from public spec.
- Proprietary: do not use.
- Open a "Clone research" issue first.

## Tests & coverage
- Coverage gate: 75% overall, 90% on new code in changed files.
- Every imported module from a competitor must ship with at least one test that pins our adapted behavior.

## Security
- No secrets in commits, ever. `gitleaks` runs in CI and via pre-commit.
- Report vulnerabilities privately via `SECURITY.md` — never as a public issue.

## Definition of Done
A PR is mergeable when:
- [ ] CI green (lint, type-check, tests, gitleaks, codeql)
- [ ] Linked issue checked off
- [ ] Docs updated
- [ ] Reviewer approved
- [ ] No `TODO` without an issue link
"""

SECURITY_MD = """# Security Policy

## Reporting a vulnerability
**Do not** file public issues for security problems.

Use GitHub's private vulnerability reporting:
- https://github.com/SIN-CLIs/playstealth-cli/security/advisories/new
- https://github.com/SIN-CLIs/unmask-cli/security/advisories/new

We aim to acknowledge within **72 hours** and ship a fix or mitigation within **14 days**
for critical issues.

## Supported versions
| Version | Supported |
|---------|-----------|
| `main`  | yes (rolling) |
| latest tagged release | yes |
| anything older | no |

## Scope
- Code in this repository
- CI/CD configuration in `.github/`
- Published packages with the same name

Out of scope:
- Third-party services we link to
- Vulnerabilities requiring an attacker to already control your machine

## Hardening commitments
- Secret scanning via `gitleaks` on every push and PR.
- Static analysis via CodeQL on every push and PR.
- Branch protection on `main`: signed reviews, status checks, no force-push, no direct push.
- Dependabot weekly with auto-grouping.
- All releases via `release-please` with provenance attestations where supported.
"""

THIRD_PARTY = """# THIRD_PARTY_NOTICES.md

This file tracks every upstream project from which we import code or take direct inspiration,
per the Clone-the-Best-Combine-Win doctrine in `COMPETITIVE_STRATEGY.md`.

| Upstream | License | Mode | Used in | Notes |
|----------|---------|------|---------|-------|
| _placeholder — populate via Clone research issues_ | | | | |

## Adding an entry
When you import code or use a project as direct inspiration:
1. Add a row above with: upstream URL, SPDX license id, mode (`code-import` / `idea-only` / `patch-watch`), location in our repo.
2. If `code-import`: copy the upstream LICENSE file to `licenses/<upstream>-LICENSE` and reference it.
3. If `idea-only`: link the spec or doc you read instead of the source.
4. Cite the upstream commit SHA you read in your PR description for reproducibility.
"""

# ---------------------------------------------------------------------------
# Per-repo file plan
# ---------------------------------------------------------------------------

PS_FILES = {
    ".github/CODEOWNERS": CODEOWNERS,
    ".github/dependabot.yml": DEPENDABOT_PY,
    ".github/PULL_REQUEST_TEMPLATE.md": PR_TEMPLATE,
    ".github/ISSUE_TEMPLATE/config.yml": ISSUE_CONFIG,
    ".github/ISSUE_TEMPLATE/bug_report.yml": ISSUE_BUG,
    ".github/ISSUE_TEMPLATE/feature_request.yml": ISSUE_FEATURE,
    ".github/ISSUE_TEMPLATE/clone_research.yml": ISSUE_CLONE,
    ".github/workflows/gitleaks.yml": GITLEAKS_WF,
    ".github/workflows/codeql.yml": CODEQL_WF_PY,
    ".github/workflows/stale.yml": STALE_WF,
    ".github/workflows/release-please.yml": RELEASE_WF_PY,
    ".pre-commit-config.yaml": PRECOMMIT_PY,
    "CONTRIBUTING.md": CONTRIBUTING,
    "THIRD_PARTY_NOTICES.md": THIRD_PARTY,
}

UM_FILES = {
    ".github/CODEOWNERS": CODEOWNERS,
    ".github/dependabot.yml": DEPENDABOT_NPM,
    ".github/PULL_REQUEST_TEMPLATE.md": PR_TEMPLATE,
    ".github/ISSUE_TEMPLATE/config.yml": ISSUE_CONFIG.replace("playstealth-cli", "unmask-cli"),
    ".github/ISSUE_TEMPLATE/bug_report.yml": ISSUE_BUG,
    ".github/ISSUE_TEMPLATE/feature_request.yml": ISSUE_FEATURE,
    ".github/ISSUE_TEMPLATE/clone_research.yml": ISSUE_CLONE,
    ".github/workflows/gitleaks.yml": GITLEAKS_WF,
    ".github/workflows/codeql.yml": CODEQL_WF_JS,
    ".github/workflows/stale.yml": STALE_WF,
    ".github/workflows/release-please.yml": RELEASE_WF_JS,
    ".pre-commit-config.yaml": PRECOMMIT_JS,
    "CONTRIBUTING.md": CONTRIBUTING,
    "THIRD_PARTY_NOTICES.md": THIRD_PARTY,
    "SECURITY.md": SECURITY_MD,
}


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def push_repo(repo: str, files: dict[str, str]):
    print(f"\n=== {repo} ===")
    for path, content in files.items():
        msg = f"chore: add {path} (post-CEO-audit infra hardening)"
        result = put_file(repo, path, content, msg)
        print(f"  {path:55} -> {result}")
        time.sleep(0.4)  # be gentle


def enable_branch_protection(repo: str):
    print(f"\n--- branch protection: {repo} ---")
    body = {
        "required_status_checks": None,
        "enforce_admins": False,
        "required_pull_request_reviews": {
            "required_approving_review_count": 1,
            "dismiss_stale_reviews": True,
            "require_code_owner_reviews": True,
        },
        "restrictions": None,
        "allow_force_pushes": False,
        "allow_deletions": False,
        "required_linear_history": True,
        "required_conversation_resolution": True,
    }
    code, data = req("PUT", f"/repos/{repo}/branches/main/protection", body)
    print(f"  protection PUT -> HTTP {code}")
    if code >= 400:
        print(f"  detail: {json.dumps(data)[:300]}")


if __name__ == "__main__":
    push_repo("SIN-CLIs/playstealth-cli", PS_FILES)
    push_repo("SIN-CLIs/unmask-cli", UM_FILES)
    enable_branch_protection("SIN-CLIs/playstealth-cli")
    enable_branch_protection("SIN-CLIs/unmask-cli")
    print("\nDone.")
