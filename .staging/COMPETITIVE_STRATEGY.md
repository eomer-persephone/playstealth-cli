# Competitive Strategy — Clone the Best, Combine, Win

**Status:** Active · **Owner:** CEO · **Reviewed:** 2026-04-28 · **Companion to:** PLAN.md, ROADMAP.md

---

## Doctrine

We do **not** invent what already exists. We:

1. **Audit** every leading competitor's killer feature.
2. **Clone** it (license-permitting) into our codebase, attributed where required.
3. **Combine** the best ideas from N projects into a single unified surface no single competitor offers.
4. **Differentiate via integration, not invention** — our moat is *cohesion*, not novelty.

> "Good artists copy. Great artists steal — and put the receipts in the THIRD_PARTY_NOTICES." — adapted

This doctrine **explicitly overrides any "build it from scratch" instinct**. If a feature already has a reference implementation in OSS, we start from that reference unless legal/license review says otherwise.

---

## License-Triage Matrix (must-do BEFORE cloning)

| License of source | Can we copy code? | Can we copy ideas/API? | Required attribution |
|---|---|---|---|
| MIT, BSD, Apache-2.0 | Yes | Yes | License + NOTICE in `THIRD_PARTY_NOTICES.md` |
| MPL-2.0 | Yes (file-level copyleft) | Yes | Keep file headers, mark modifications |
| LGPL-3.0 | Dynamically link only | Yes | Notice + relink obligation |
| GPL-3.0 / AGPL-3.0 | **No** (would taint our codebase) | Yes (clean-room API only) | None — **must reimplement** |
| Proprietary / no license | **No code** | Public API surface only | None |

**Process:** Every clone-issue MUST cite the source license in its body. PR review checks for `THIRD_PARTY_NOTICES.md` updates.

---

## Target Competitors & Killer Features

### Browser Automation / LLM Agents (relevant for `unmask-cli`)

| Project | License | Stars | Killer feature we want | Our issue |
|---|---|---|---|---|
| [Browser-Use](https://github.com/browser-use/browser-use) | MIT | ~50k | DOM-tree-to-LLM serializer with element indices, vision fallback, action history | UM-CLONE-1 |
| [Stagehand](https://github.com/browserbase/stagehand) | MIT | ~8k | `observe(intent)` / `extract(zodSchema)` / `act(intent)` typed API | UM-CLONE-2 |
| [Skyvern](https://github.com/Skyvern-AI/skyvern) | AGPL-3.0 | ~10k | Vision-first action planning, workflow YAML — **idea-only clone** | UM-CLONE-3 |
| [Playwright MCP](https://github.com/microsoft/playwright-mcp) | Apache-2.0 | growing | MCP server surface, accessibility-tree snapshots | UM-CLONE-4 |
| [Steel-Browser](https://github.com/steel-dev/steel-browser) | Apache-2.0 | ~3k | Session API, recorder, replay, proxy abstraction | UM-CLONE-5 |
| [Puppeteer](https://github.com/puppeteer/puppeteer) | Apache-2.0 | ~88k | CDP-level primitives, stable API patterns | UM-CLONE-6 |
| [Auto-Playwright](https://github.com/lucgagan/auto-playwright) | MIT | small | Natural-language test step → Playwright command | UM-CLONE-7 |
| [LaVague](https://github.com/lavague-ai/LaVague) | Apache-2.0 | ~6k | World-model + action engine separation | UM-CLONE-8 |

### Stealth / Anti-Detection (relevant for `playstealth-cli`)

| Project | License | Stars | Killer feature we want | Our issue |
|---|---|---|---|---|
| [playwright-stealth](https://github.com/AtuboDad/playwright_stealth) | MIT | ~1k | Evasion script collection (canvas, webgl, navigator) | PS-CLONE-1 |
| [undetected-chromedriver](https://github.com/ultrafunkamsterdam/undetected-chromedriver) | GPL-3.0 | ~12k | Cloudflare bypass tactics — **idea-only clone** | PS-CLONE-2 |
| [camoufox](https://github.com/daijro/camoufox) | MPL-2.0 | ~3k | Firefox-based fingerprint at C-level, font/locale spoofing | PS-CLONE-3 |
| [botright](https://github.com/Vinyzu/Botright) | GPL-3.0 | ~1k | Captcha-solver routing — **idea-only clone**, MIT solver libs | PS-CLONE-4 |
| [patchright-python](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright-python) | LGPL-3.0 | ~1k | Patched Playwright with built-in evasions | PS-CLONE-5 |
| [rebrowser-patches](https://github.com/rebrowser/rebrowser-patches) | MIT | ~1k | Runtime.Enable leak patches | PS-CLONE-6 |
| [CreepJS](https://github.com/abrahamjuliot/creepjs) | MIT | ~3k | Detection vectors as our **test oracle** | PS-CLONE-7 |
| [BrowserForge](https://github.com/daijro/browserforge) | Apache-2.0 | ~1k | Realistic header+fingerprint generator | PS-CLONE-8 |

---

## Combine Layer — How we win

No single competitor offers the full stack:

```
┌─────────────────────────────────────────────────────────────────┐
│                   Our Combined Surface                          │
├─────────────────────────────────────────────────────────────────┤
│  observe / extract / act        ← Stagehand-style API           │
│  +  DOM-tree LLM serializer     ← Browser-Use                   │
│  +  vision fallback             ← Browser-Use / Skyvern         │
│  +  HAR + trace + screenshots   ← native Playwright (forensic)  │
│  +  stealth fingerprint         ← camoufox + BrowserForge       │
│  +  evasion script collection   ← playwright-stealth + patchright│
│  +  CreepJS CI score gate       ← CreepJS as oracle             │
│  +  MCP server surface          ← Playwright MCP                │
│  +  session record/replay       ← Steel-Browser                 │
│  +  self-healing selectors      ← our innovation                │
│  +  auto-issue/PR reporter      ← our innovation                │
└─────────────────────────────────────────────────────────────────┘
```

**The two cells at the bottom are our only "from scratch" investments.** Everything else is cloned + combined + licensed properly.

---

## Working Agreement — every clone PR must include

- [ ] Source repo + commit SHA + license cited in PR body
- [ ] `THIRD_PARTY_NOTICES.md` updated (file added/modified entries)
- [ ] No GPL/AGPL **code** copied (idea-only clones must include a "clean-room note" in PR)
- [ ] Adapted to our code style + tests + types
- [ ] At least one test that proves parity with the source feature
- [ ] CHANGELOG entry: `cloned from <project>@<sha>`

---

## Anti-Patterns We Will NOT Repeat

- "We can build this better from scratch" → 90 % of the time we cannot, in the time we have.
- Forking entire repos and pretending — we always cite.
- Cloning without license review — legal owns this gate.
- Cloning without writing the parity test — un-testable clone = dead code.

---

## Decision Log

| Date | Decision | Rationale |
|---|---|---|
| 2026-04-28 | Adopt Clone-Combine doctrine | Competitors are years ahead; greenfield is suicide |
| 2026-04-28 | Issues PS-CLONE-1..8 + UM-CLONE-1..8 created | Concrete tickets per competitor |
| 2026-04-28 | GPL/AGPL → idea-only | Avoid copyleft taint of MIT-licensed core |
