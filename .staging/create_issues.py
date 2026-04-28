#!/usr/bin/env python3
"""Create all audit issues in both SIN-CLIs repos via REST API.

Reads token from env GH_TOKEN.
"""
import json
import os
import sys
import urllib.request
import urllib.error

TOKEN = os.environ["GH_TOKEN"]


def post(url: str, payload: dict) -> dict:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"token {TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "v0-ceo-audit",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"_error": e.code, "_body": e.read().decode()[:300]}


# ────────────────────────── playstealth-cli ──────────────────────────
PS_REPO = "SIN-CLIs/playstealth-cli"

PS_ISSUES = [
    {
        "title": "[Audit/P0] Resilience Engine — fill empty test files (#11 follow-up)",
        "body": """## Context (from CEO audit 2026-04-28)

Issue #11 was closed as COMPLETED but the resilience engine ships **without working tests**:

| File | Test functions |
|---|---|
| `tests/test_resilience_config.py` | 0 |
| `tests/test_github_issue_reporter.py` | 0 |
| `tests/test_auto_heal_selector.py` | 0 |
| `tests/test_secret_manager.py` | 0 |

## Acceptance criteria

- [ ] `test_resilience_config.py`: covers config loading, defaults, overrides, singleton behaviour, env-var precedence
- [ ] `test_github_issue_reporter.py`: covers JWT generation, dedup window, template selection (selector vs general), HTTP retry, redaction of secrets in issue body
- [ ] `test_auto_heal_selector.py`: covers fallback chain (primary → testid → aria → role+name → text), confidence scoring, persistence of healed selector
- [ ] `test_secret_manager.py`: covers key loading, rotation, missing-secret error path, no-leak guarantee in `__repr__`/`__str__`
- [ ] Coverage of these four modules ≥ 85 %
- [ ] CI fails if any of these test files has 0 collected tests
- [ ] Resilience-related closed issues (#11) re-validated

Linked: #11 (reopened)
""",
        "labels": ["audit", "tests", "tech-debt", "priority-p0"],
    },
    {
        "title": "[Audit/P0] Fix `demo` command broken after pipx install (top-level import)",
        "body": """## Context

`playstealth_cli.py` does:

```python
from demo_flow import run_demo
```

This **breaks** after `pipx install playstealth-cli` because `demo_flow` is not part of the installed package — it lives at repo root.

## Acceptance criteria

- [ ] Move `demo_flow.py` into the `playstealth_actions` package (or a dedicated `playstealth_cli/demo/` module).
- [ ] Update import to package-relative: `from playstealth_actions.demo_flow import run_demo`.
- [ ] Add a smoke test that runs `playstealth demo --dry-run` after a fresh wheel install.
- [ ] Document in README the new import path.
""",
        "labels": ["bug", "audit", "priority-p0"],
    },
    {
        "title": "[Audit/P0] Security: rotate leaked NVIDIA key + remove from git history (#9)",
        "body": """## Context

Leaked NVIDIA API key in `.env` at commit `bb966f8` (see #9). Action plan tracked here as a P0 item.

## Acceptance criteria

- [ ] Key rotated in https://build.nvidia.com/
- [ ] No code references the leaked key
- [ ] Git history rewritten via `git filter-repo --invert-paths --path .env`
- [ ] Force-push coordinated, all collaborators notified
- [ ] `.env` confirmed in `.gitignore`, `.env.example` contains only placeholders
- [ ] gitleaks pre-commit hook added (`.pre-commit-config.yaml`)
- [ ] CI gitleaks job added that fails on new secrets
- [ ] Issue #9 closed only after all 7 boxes ticked

Linked: #9
""",
        "labels": ["security", "audit", "priority-p0"],
    },
    {
        "title": "[Audit/P0] Stealth-score CI gate (CreepJS / SannySoft) with stored artifact",
        "body": """## Context

`diagnose_benchmark.py` exists but there is **no reproducible stealth score** in the repo, no CI gate, no artifact.
Our entire "Anti-Detection-Engine" claim is unverified.

## Acceptance criteria

- [ ] CI workflow `.github/workflows/stealth-bench.yml` runs on every PR + nightly
- [ ] Job launches headless browser, hits `https://bot.sannysoft.com/` and `https://abrahamjuliot.github.io/creepjs/`
- [ ] Parses score, uploads HTML + JSON as artifact (retention 30 d)
- [ ] Asserts CreepJS lie-count ≤ N (configurable, initial threshold from baseline run)
- [ ] Asserts SannySoft "Passed" tests ≥ M
- [ ] Score history written to `bench/history.jsonl` (append-only)
- [ ] README badge linking to latest score artifact
""",
        "labels": ["ci", "tests", "audit", "priority-p0"],
    },
    {
        "title": "[Audit/P0] Test-coverage gate ≥ 75 % in CI (pytest-cov)",
        "body": """## Acceptance criteria

- [ ] `pyproject.toml` adds `coverage` + `pytest-cov` to dev deps
- [ ] CI runs `pytest --cov=playstealth_actions --cov-fail-under=75`
- [ ] HTML coverage uploaded as artifact
- [ ] README badge for coverage
- [ ] Document in HACKING.md how to read + improve coverage locally
""",
        "labels": ["ci", "tests", "audit", "priority-p0"],
    },
    {
        "title": "[Audit/P1] Version hygiene — release v1.0.0 to PyPI OR rebrand to 0.9.0-beta",
        "body": """## Context

Current state:
- `pyproject.toml` declares version `1.0.0`
- README shows a PyPI badge
- **Package is NOT on PyPI** → trust damage on first visit

## Decision required

Pick ONE:
- **A.** Release v1.0.0 to PyPI (after #11 follow-up + stealth-score CI is green)
- **B.** Rebrand version to `0.9.0-beta`, remove PyPI badge until A is done

## Acceptance criteria

- [ ] Decision logged in PLAN.md ADR table
- [ ] Either tag pushed + `twine upload` executed + post-release smoke test
- [ ] OR version bumped down + badge removed + README "Beta" disclaimer added
""",
        "labels": ["devex", "audit", "priority-p1"],
    },
    {
        "title": "[Audit/P1] `playstealth init` interactive setup wizard",
        "body": """## Context

Current onboarding requires ≥ 6 env vars, plugin understanding, Playwright browser install, and stealth profile validation — without a guided wizard. First-run friction is high.

## Acceptance criteria

- [ ] New subcommand `playstealth init` (Python `prompt_toolkit` or `questionary`)
- [ ] Wizard collects: project dir, default plugin, GitHub App config (optional), telemetry opt-in/out, secret storage choice
- [ ] Writes `.env` from template + creates `~/.playstealth/config.toml`
- [ ] Runs `playwright install chromium` if missing
- [ ] Runs `playstealth doctor` at the end
- [ ] Idempotent (`init --force` re-runs, otherwise asks)
- [ ] Smoke test in CI
""",
        "labels": ["devex", "audit", "priority-p1"],
    },
    {
        "title": "[Audit/P1] Language unification — all CLI strings to English (i18n later)",
        "body": """## Context

CLI mixes German and English in user-facing output. International OSS adoption requires English baseline.

## Acceptance criteria

- [ ] All strings in `playstealth_cli.py` and `playstealth_actions/**/*.py` translated to English
- [ ] No emoji prefixes in machine-readable output (only in TUI/dashboard)
- [ ] All exception messages, docstrings, log messages: English
- [ ] Optional: scaffold for `gettext`-based i18n (postponed to ice-box)
- [ ] `grep -nE 'ä|ö|ü|ß|Erfolgreich|Fehler|Unbekannter'` returns nothing in source
""",
        "labels": ["devex", "audit", "priority-p1"],
    },
    {
        "title": "[Audit/P1] Carve out vertical plugins (`hey_piggy.py`, `qualtrics.py`) into separate repo",
        "body": """## Context (Reputation/Compliance)

Platform-specific reward-survey plugins in the core repo cause:
- Compliance/legal exposure (most platform ToS forbid automation)
- Optics: tool *looks* like fraud-tooling
- Hard coupling between neutral framework and dubious verticals

## Acceptance criteria

- [ ] Create new repo `SIN-CLIs/playstealth-vertical-plugins`
- [ ] Move `playstealth_actions/plugins/hey_piggy.py`, `qualtrics.py` (and any platform-specific helpers) there
- [ ] Document plugin discovery via entry points so external plugins still work
- [ ] Core README rebranded as "neutral stealth + QA-test framework"
- [ ] COMPLIANCE.md updated to reflect new boundary
- [ ] Add deprecation shim in core for one minor version
""",
        "labels": ["audit", "tech-debt", "priority-p1"],
    },
    {
        "title": "[Audit/P2] DX polish — `--version`, shell completion, structured error codes (PSE-XXXX)",
        "body": """## Acceptance criteria

- [ ] `playstealth --version` prints semver + commit + Python version
- [ ] Shell completions generated via `argcomplete` for bash/zsh/fish, install hook in CI/release notes
- [ ] All raised exceptions get a stable code: `PSE-1xxx` (config), `PSE-2xxx` (browser), `PSE-3xxx` (network), `PSE-4xxx` (plugin), `PSE-5xxx` (resilience)
- [ ] `errors.md` documents every code with cause + fix
- [ ] CLI prints code + short message + link to docs
""",
        "labels": ["devex", "audit", "priority-p2"],
    },
    {
        "title": "[Audit/P2] Performance benchmark suite (Surveys/h, RAM, browser-lifetime)",
        "body": """## Acceptance criteria

- [ ] `bench/` directory with deterministic, reproducible bench scripts
- [ ] Measures: surveys/hour (simulator), peak RSS, browser-context lifetime, time-to-first-action
- [ ] CI workflow runs nightly, posts results as commit comment + artifact
- [ ] README table comparing our numbers vs. published numbers from playwright-stealth + nodriver + camoufox
- [ ] Trend graph generated from `bench/history.jsonl`
""",
        "labels": ["audit", "priority-p2"],
    },
    {
        "title": "[Audit/P0] Soften pre-flight check — make it warn-only by default, opt-in `--strict-preflight`",
        "body": """## Context

`preflight_check()` in `playstealth_cli.py` calls `sys.exit(1)` on any failed check. This blocks power users and CI environments where some checks are intentionally absent (e.g. no GitHub App key).

## Acceptance criteria

- [ ] Default behaviour: print warnings, continue
- [ ] New flag `--strict-preflight` to keep current hard-fail behaviour
- [ ] `playstealth doctor` becomes the **diagnostic** command (always runs all checks, no exit codes)
- [ ] README + HACKING document the change
- [ ] Test coverage for both modes
""",
        "labels": ["bug", "devex", "audit", "priority-p0"],
    },
]

# ────────────────────────── unmask-cli ──────────────────────────
UM_REPO = "SIN-CLIs/unmask-cli"

UM_ISSUES = [
    {
        "title": "[Audit/P0] Test-coverage gate ≥ 75 % in CI (vitest --coverage)",
        "body": """## Acceptance criteria

- [ ] `vitest.config.ts` has `coverage.thresholds.lines = 75` (and branches/functions/statements)
- [ ] CI runs `vitest run --coverage` and uploads HTML + lcov
- [ ] README badge for coverage
- [ ] HACKING documents how to read coverage locally
""",
        "labels": ["audit", "tests", "priority-p0"],
    },
    {
        "title": "[Audit/Meta] Single-main-branch policy enforced + branch-protection rules",
        "body": """## Context

CEO audit 2026-04-28 mandates a single-main-branch policy across both repos.
The `migrate-branches-to-main` branch was deleted (was 0 ahead / 3 behind).

## Acceptance criteria

- [ ] Branch protection on `main`:
  - Require PR before merging
  - Require status checks to pass (typecheck, lint, test, build, coverage)
  - Require up-to-date branch
  - Dismiss stale approvals
  - Linear history
- [ ] CONTRIBUTING.md documents the single-main policy + ≤ 48 h feature-branch lifetime
- [ ] CODEOWNERS file added
""",
        "labels": ["audit", "priority-p0"],
    },
    {
        "title": "[Audit/Meta] Sprint-1 roll-up (P0 stabilisation)",
        "body": """## Roll-up issue tracking Sprint-1 P0 items from PLAN.md

Sub-issues:
- [ ] #18 postinstall hook for `playwright install chromium`
- [ ] #19 `unmask doctor` self-diagnostic CLI
- [ ] #20 self-healing selector resolver in QueueManager
- [ ] #22 real-browser E2E test against local HTML fixture
- [ ] coverage-gate ≥ 75 % (this audit batch)

DoD: all sub-issues closed, CHANGELOG entry, PLAN.md Sprint-1 section ticked.
""",
        "labels": ["epic", "audit", "priority-p0"],
    },
    {
        "title": "[Audit/Meta] Sprint-2 roll-up (P0 forensic replay)",
        "body": """## Roll-up tracking Sprint-2 P0 items

Sub-issues:
- [ ] #9 per-session HAR export
- [ ] #10 Playwright trace.zip per session
- [ ] #11 screenshot timeline
- [ ] #12 single-zip bundle exporter (`unmask bundle <session>`)

This is our **hero feature** vs Browser-Use / Stagehand / Skyvern. Must ship complete + documented.
""",
        "labels": ["epic", "audit", "priority-p0"],
    },
    {
        "title": "[Audit/Meta] Sprint-3 roll-up (P0 LLM reasoning layer)",
        "body": """## Roll-up tracking Sprint-3 LLM items

Sub-issues:
- [ ] #7 DOM-tree-to-LLM serializer (Browser-Use style)
- [ ] #4 `observe(intent)` API
- [ ] #5 `extract<T>(zodSchema)` API
- [ ] #6 `act(intent)` compound API
- [ ] #8 vision-fallback at confidence < 0.5

Without this layer we are "just a DOM scanner". This is the **competitive differentiator**.
""",
        "labels": ["epic", "audit", "priority-p0"],
    },
]


def main() -> None:
    summary = {"ps_created": [], "um_created": [], "errors": []}

    for repo, issues, key in (
        (PS_REPO, PS_ISSUES, "ps_created"),
        (UM_REPO, UM_ISSUES, "um_created"),
    ):
        url = f"https://api.github.com/repos/{repo}/issues"
        for issue in issues:
            r = post(url, issue)
            if "_error" in r:
                summary["errors"].append({"repo": repo, "title": issue["title"], **r})
                print(f"ERR  {repo}#?  {issue['title'][:70]}  {r}")
            else:
                num = r.get("number")
                summary[key].append({"number": num, "title": issue["title"]})
                print(f"OK   {repo}#{num:>3}  {issue['title'][:80]}")

    print()
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
