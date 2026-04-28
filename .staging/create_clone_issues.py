#!/usr/bin/env python3
"""Create competitive-clone issues (UM-CLONE-* and PS-CLONE-*) plus the meta tracker."""
import json
import os
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


def ensure_label(repo: str, name: str, color: str) -> None:
    url = f"https://api.github.com/repos/{repo}/labels"
    post(url, {"name": name, "color": color})


def clone_body(source_name: str, source_url: str, license_: str,
               feature: str, why: str, acceptance: list[str],
               clone_mode: str = "code") -> str:
    notes = ""
    if clone_mode == "idea-only":
        notes = ("\n> **Clone mode: idea-only.** Source license is GPL/AGPL or proprietary. "
                 "We re-implement the API surface from scratch (clean-room) and must NOT copy code. "
                 "Include a clean-room note in the PR body.\n")
    ac_md = "\n".join(f"- [ ] {item}" for item in acceptance)
    return f"""## Source

- **Project:** [{source_name}]({source_url})
- **License:** `{license_}`
- **Clone mode:** `{clone_mode}`
{notes}
## Feature we want

{feature}

## Why we want it

{why}

## Acceptance criteria

{ac_md}
- [ ] PR body cites source repo + commit SHA + license
- [ ] `THIRD_PARTY_NOTICES.md` updated
- [ ] Parity test added (proves our clone behaves like source for the relevant case)
- [ ] CHANGELOG entry: `cloned from {source_name}@<sha>`

## Reference

See `COMPETITIVE_STRATEGY.md` for the full doctrine.
"""


# ────────────────────────── unmask-cli clones ──────────────────────────
UM_REPO = "SIN-CLIs/unmask-cli"
UM = [
    ("UM-CLONE-1", "Browser-Use — DOM-tree-to-LLM serializer with element indices",
     "Browser-Use", "https://github.com/browser-use/browser-use", "MIT", "code",
     "Serialize the live DOM into a numbered, LLM-friendly tree where each interactable "
     "element gets a stable index. The LLM acts by index, not by selector — drastically "
     "reduces hallucinated selectors.",
     "Foundation for our `observe/extract/act` API. Every modern agent framework has this. "
     "Without it, our LLM layer is hopelessly behind.",
     [
         "Module `src/serialize/dom_tree.ts` exposes `serializeForLLM(page) -> {tree, indexMap}`",
         "Includes ARIA role + accessible name + bounding box + `data-testid` if present",
         "Filters non-interactable / off-screen / hidden elements",
         "Round-trip test: index → element → click works on 5 fixture pages",
         "Token-budget mode: produce <=N tokens by collapsing subtrees",
     ]),
    ("UM-CLONE-2", "Stagehand — observe()/extract()/act() typed API",
     "Stagehand", "https://github.com/browserbase/stagehand", "MIT", "code",
     "Three-verb agent surface: `observe(intent)` returns candidate actions, "
     "`extract(zodSchema)` returns typed structured data, `act(intent)` performs an action. "
     "All driven by an LLM under the hood.",
     "This is the de-facto API shape the market expects. Closes existing issues #4/#5/#6.",
     [
         "Public API: `await page.observe(intent)`, `await page.extract(schema)`, `await page.act(intent)`",
         "Zod schema validation on extract; typed return inferred from schema",
         "Configurable model provider (OpenAI/Anthropic/Vercel AI Gateway) via DI",
         "Mock-LLM mode for unit tests",
         "Examples in `examples/stagehand-style/`",
     ]),
    ("UM-CLONE-3", "Skyvern — workflow YAML + vision-first planner (idea-only)",
     "Skyvern", "https://github.com/Skyvern-AI/skyvern", "AGPL-3.0", "idea-only",
     "Declarative YAML workflow definition that the agent executes step-by-step, "
     "with vision-first planning when DOM heuristics fail.",
     "AGPL forbids code copy, but the API shape (YAML workflows + vision fallback) is public knowledge.",
     [
         "Spec doc `docs/workflow-yaml.md` defines our YAML schema (clean-room, no Skyvern code)",
         "Loader/runner in `src/workflow/runner.ts`",
         "Vision fallback hook integrates with UM-CLONE-1 serializer",
         "5 sample workflows in `examples/workflows/`",
         "PR body explicitly states clean-room implementation",
     ]),
    ("UM-CLONE-4", "Playwright MCP — accessibility-tree snapshots + MCP server surface",
     "Playwright MCP", "https://github.com/microsoft/playwright-mcp", "Apache-2.0", "code",
     "Microsoft's MCP server exposes browser actions as MCP tools and uses accessibility-tree "
     "snapshots (cheaper than vision, more reliable than DOM dumps).",
     "MCP is becoming the integration layer for AI tooling. Native MCP support = instant "
     "compatibility with Claude Desktop, Cursor, every MCP client.",
     [
         "`unmask mcp` subcommand starts an MCP server (stdio + SSE transports)",
         "Tools exposed: `navigate`, `click`, `type`, `snapshot`, `extract`, `observe`",
         "Snapshots use Playwright's `aria-snapshot` API where possible",
         "Conformance test against MCP spec",
         "README section on MCP usage",
     ]),
    ("UM-CLONE-5", "Steel-Browser — session record/replay + proxy abstraction",
     "Steel-Browser", "https://github.com/steel-dev/steel-browser", "Apache-2.0", "code",
     "First-class session lifecycle (create/resume/destroy), built-in recorder/replay, "
     "proxy rotation abstraction.",
     "Pairs perfectly with our forensic-replay hero feature. Session API is the missing "
     "user-facing surface around our HAR+trace bundle.",
     [
         "`SessionManager` class with create/resume/destroy/list",
         "Recorder writes to our existing bundle format (HAR+trace+screenshots)",
         "Replay subcommand `unmask replay <session-id>`",
         "Proxy abstraction with rotating-proxy adapter interface",
         "Integration test: record → replay → assert identical DOM",
     ]),
    ("UM-CLONE-6", "Puppeteer — stable CDP-level primitives we can re-export",
     "Puppeteer", "https://github.com/puppeteer/puppeteer", "Apache-2.0", "code",
     "Puppeteer's `Page`, `Frame`, `Browser` API patterns are the most battle-tested in the "
     "ecosystem. We mirror the parts that don't conflict with Playwright's surface.",
     "Lowers learning curve for the millions of devs who already know Puppeteer.",
     [
         "Compatibility wrapper `src/compat/puppeteer.ts` exposing puppeteer-shaped API",
         "Documented in `docs/migration-from-puppeteer.md`",
         "Smoke tests for the most-used 20 methods",
     ]),
    ("UM-CLONE-7", "Auto-Playwright — natural-language step → Playwright command",
     "Auto-Playwright", "https://github.com/lucgagan/auto-playwright", "MIT", "code",
     "Translates a single natural-language sentence into a Playwright command. Smaller scope "
     "than Stagehand `act()`, useful for QA-test authoring.",
     "Powers our `unmask record --nl` and lowers the bar for non-engineers writing tests.",
     [
         "`auto(intent, page)` helper exported",
         "5 NL→action mappings tested against fixture pages",
         "Caches translations (intent → action) keyed by page URL hash",
         "CLI: `unmask auto \"click the submit button\"`",
     ]),
    ("UM-CLONE-8", "LaVague — World-model / Action-engine separation",
     "LaVague", "https://github.com/lavague-ai/LaVague", "Apache-2.0", "code",
     "Architectural pattern: a *World-Model* (LLM-driven planner) is decoupled from an "
     "*Action-Engine* (deterministic executor). Cleaner than monolithic agents.",
     "Forces a clean architecture inside our agent layer. Easier to test, easier to swap models.",
     [
         "`src/agent/world_model.ts` — pure planner, LLM-only, returns action list",
         "`src/agent/action_engine.ts` — deterministic executor, no LLM calls",
         "Interface contract documented in `docs/architecture.md`",
         "Unit tests for both halves are independent (action engine has zero LLM mocks)",
     ]),
]

# ────────────────────────── playstealth-cli clones ──────────────────────────
PS_REPO = "SIN-CLIs/playstealth-cli"
PS = [
    ("PS-CLONE-1", "playwright-stealth — full evasion script collection",
     "playwright-stealth", "https://github.com/AtuboDad/playwright_stealth", "MIT", "code",
     "Comprehensive set of JS evasion scripts: `chrome.runtime`, `navigator.webdriver`, "
     "`navigator.plugins`, `navigator.languages`, `WebGL vendor`, `iframe.contentWindow`, "
     "media-codecs, etc.",
     "Industry baseline. Anyone benchmarking us against playwright-stealth must see at least parity.",
     [
         "`playstealth_actions/evasions/` mirrors the 15+ scripts from the source",
         "Each script has a unit test asserting the expected `navigator.*` value after injection",
         "CreepJS score with all scripts on > score with playwright-stealth alone",
         "License header preserved on each ported file (MIT)",
         "`THIRD_PARTY_NOTICES.md` lists playwright-stealth",
     ]),
    ("PS-CLONE-2", "undetected-chromedriver — Cloudflare bypass tactics (idea-only)",
     "undetected-chromedriver", "https://github.com/ultrafunkamsterdam/undetected-chromedriver", "GPL-3.0", "idea-only",
     "Tactics for passing Cloudflare's `cf_clearance` flow: timing, mouse movement, JS-challenge "
     "passing without interaction.",
     "GPL forbids code copy. Tactics are public knowledge; we re-implement clean-room.",
     [
         "`docs/cloudflare-bypass.md` describes our clean-room approach",
         "Implementation in `playstealth_actions/evasions/cloudflare.py` (no GPL imports)",
         "PR body includes clean-room declaration",
         "Integration test against a Cloudflare-protected fixture site",
     ]),
    ("PS-CLONE-3", "camoufox — Firefox C-level fingerprint manipulation",
     "camoufox", "https://github.com/daijro/camoufox", "MPL-2.0", "code",
     "Patched Firefox build with C-level fingerprint controls (fonts, screen, locale, timezone, "
     "WebRTC). Strongest stealth on the market for Firefox.",
     "Adds Firefox as a first-class stealth target. Many detection vectors only fire on Chromium.",
     [
         "Optional Firefox launcher `playstealth_actions/launchers/camoufox.py`",
         "Documented binary download (we do NOT vendor the patched build)",
         "Profile builder mirrors camoufox's config schema (font list, screen size, etc.)",
         "MPL file headers preserved on any copied logic",
         "CreepJS Firefox baseline run added to bench suite",
     ]),
    ("PS-CLONE-4", "botright — captcha-solver routing (idea-only)",
     "botright", "https://github.com/Vinyzu/Botright", "GPL-3.0", "idea-only",
     "Detect-and-route architecture for captcha solving: hCaptcha / reCAPTCHA / FunCaptcha → "
     "appropriate solver service.",
     "GPL forbids code copy. The routing pattern + service abstractions are clean-room cloneable. "
     "Solvers themselves stay external (not bundled).",
     [
         "`playstealth_actions/captcha/router.py` with detect→route abstraction",
         "Adapter interface for external solver services (no API keys bundled)",
         "Unit tests with mocked solvers",
         "PR includes clean-room declaration",
     ]),
    ("PS-CLONE-5", "patchright — patched Playwright base for built-in evasions",
     "patchright-python", "https://github.com/Kaliiiiiiiiii-Vinyzu/patchright-python", "LGPL-3.0", "code",
     "Patches the Playwright driver itself to remove leaks (`Runtime.Enable`, `target.id`, etc.) "
     "that pure JS-injection cannot fix.",
     "Driver-level leaks are detectable regardless of how clean our injected JS is. This closes "
     "the last category of fingerprints.",
     [
         "Optional dependency: `playstealth[patchright]` extra installs patchright as Playwright replacement",
         "LGPL relink obligation documented in `THIRD_PARTY_NOTICES.md`",
         "Detection-leak test (`Runtime.Enable` probe) passes with patchright extra",
         "Falls back gracefully if extra not installed",
     ]),
    ("PS-CLONE-6", "rebrowser-patches — Runtime.Enable leak fix",
     "rebrowser-patches", "https://github.com/rebrowser/rebrowser-patches", "MIT", "code",
     "Specific patch for the `Runtime.Enable` CDP leak that even patchright doesn't fully cover.",
     "Belt + suspenders for the most-checked CDP leak.",
     [
         "Patch applied either via patchright extra or as a runtime CDP filter we own",
         "Test asserts `Runtime.Enable` does not appear in CDP traffic during navigation",
         "MIT attribution preserved",
     ]),
    ("PS-CLONE-7", "CreepJS — use as our test oracle (not clone — adopt as benchmark target)",
     "CreepJS", "https://github.com/abrahamjuliot/creepjs", "MIT", "code",
     "We do NOT clone CreepJS. We use it as the **oracle** in our CI score gate "
     "(see audit issue #34).",
     "Closes audit issue #34 by formally adopting CreepJS as our benchmark target.",
     [
         "Pinned CreepJS commit referenced in CI workflow",
         "Score history written to `bench/creepjs/history.jsonl`",
         "MIT attribution in `THIRD_PARTY_NOTICES.md`",
     ]),
    ("PS-CLONE-8", "BrowserForge — realistic header + fingerprint generator",
     "BrowserForge", "https://github.com/daijro/browserforge", "Apache-2.0", "code",
     "Generates statistically realistic browser headers + fingerprints (UA, Accept-Language, "
     "screen size, etc.) drawn from real-world distributions.",
     "Replaces our hand-crafted persona profiles with a data-driven generator. Higher realism, "
     "less manual maintenance.",
     [
         "`playstealth_actions/fingerprint/forge.py` wraps BrowserForge",
         "Persona-Manager can opt into BrowserForge profiles",
         "Apache-2.0 attribution in `THIRD_PARTY_NOTICES.md`",
         "Test compares old vs new persona realism via CreepJS score",
     ]),
]


def make_issues(repo: str, items: list, label_set: list[str]) -> list[dict]:
    out = []
    url = f"https://api.github.com/repos/{repo}/issues"
    for tag, title_short, src_name, src_url, lic, mode, feature, why, ac in items:
        title = f"[{tag}] {title_short}"
        body = clone_body(src_name, src_url, lic, feature, why, ac, clone_mode=mode)
        r = post(url, {"title": title, "body": body, "labels": label_set})
        if "_error" in r:
            print(f"ERR  {repo}  {tag}  {r}")
        else:
            print(f"OK   {repo}#{r.get('number')}  {tag}")
        out.append(r)
    return out


def main() -> None:
    # Make sure labels exist (idempotent)
    for repo in (UM_REPO, PS_REPO):
        for name, color in [
            ("clone", "8a63d2"),
            ("competitive", "0e8a16"),
            ("priority-p1", "d93f0b"),
            ("priority-p2", "fbca04"),
        ]:
            ensure_label(repo, name, color)

    print("=== unmask-cli clone issues ===")
    make_issues(UM_REPO, UM, ["clone", "competitive", "priority-p1"])

    print("\n=== playstealth-cli clone issues ===")
    make_issues(PS_REPO, PS, ["clone", "competitive", "priority-p1"])


if __name__ == "__main__":
    main()
