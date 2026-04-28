# unmask-cli — Master PLAN (Single Source of Truth)

> **Status:** TypeScript Implementation in `main` (PR #3 gemergt) · main = Source of Truth
> **Owner:** SIN-CLIs/unmask-cli
> **Letztes Audit:** 2026-04-28
> **Companion-Repo:** [SIN-CLIs/playstealth-cli](https://github.com/SIN-CLIs/playstealth-cli)

---

## 0. Working Agreement (verbindlich)

1. **Single-Branch-Policy** — alle Arbeit landet auf `main`. Feature-Branches <= 48 h, Squash-Merge, sofort geloescht.
2. **No half-done issues** — Schliessen erst wenn Code + Tests + Doku.
3. **CI = Gate** — typecheck, lint, vitest, build muessen gruen sein.
4. **Strict TypeScript** — `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes` bleiben hart.
5. **Sprache** — Code, Doku, CLI-Output: **Englisch**.

---

## 1. Aktueller Stand

### Was funktioniert (auf main)
- `unmask-network` (CDP-Sniffer mit Fallback)
- `unmask-dom` (semantischer Scanner mit prioritisierten Selectors)
- `unmask-console` (Console + pageerror Listener)
- Self-healing Selector Chain
- Persistente Queue + Atomic State (`~/.unmask/state.json`)
- 20 vitest unit tests gruen
- ESLint, Prettier, GH-Actions CI

### Audit-Befunde
- `migrate-branches-to-main` Branch ist **0 ahead, 3 behind** main -> **stale, loeschen**.
- 44 offene Issues — viele Epics + Sub-Issues, sauber strukturiert, aber bisher keine sichtbare Sprint-Priorisierung.
- Kein zentrales PLAN/ROADMAP-Dokument bisher.
- Keine LLM-Layer (#27, #4–#8 offen) — das ist der **groesste Funktionsblock** und unser Differenzierer.

---

## 2. Strategische Positionierung

**Wettbewerb:** `Stagehand` (Browserbase), `Browser Use`, `Skyvern`, `BrowserAgent`, `Multion`.

**Unser USP:**
1. **Sense-Layer fuer Agents** — wir sind das "Roentgengeraet", nicht der ganze Agent. Composable.
2. **Forensic Replay** — HAR + trace.zip + screenshot timeline pro Session (#9–#13). Niemand macht das so vollstaendig.
3. **Self-Healing-Selectors out-of-the-box** ohne LLM-Calls.
4. **Sequential Queue + Persona-System** als reproduzierbare Test-Harness.

**Sense + Act Stack:** unmask-cli (sense) + playstealth-cli (act) gekoppelt via JSON-RPC ist die Story.

---

## 3. 90-Tage-Roadmap

### Sprint 1 — Stabilisierung & Self-Diagnostics (Woche 1–2) — **P0**
- [ ] #18 postinstall hook fuer `playwright install chromium`
- [ ] #19 `unmask doctor` self-diagnostic CLI
- [ ] #20 Self-healing Selector Resolver in QueueManager verdrahten
- [ ] #22 Real-Browser E2E Test gegen lokales HTML-Fixture
- [ ] **NEU:** Coverage-Gate >= 75 % in CI

### Sprint 2 — Forensic Replay (Woche 3–4) — **P0**
- [ ] #9 Per-Session HAR-Export
- [ ] #10 Playwright trace.zip pro Session
- [ ] #12 Single-Zip Bundle Exporter (`unmask bundle <session>`)
- [ ] #11 Screenshot-Timeline (jede Action + on failure)

### Sprint 3 — LLM Reasoning Layer (Woche 5–7) — **P0/P1**
- [ ] #7 DOM-Tree-to-LLM Serializer (Browser-Use-Style)
- [ ] #4 `observe(intent)` API mit ranked candidates
- [ ] #5 `extract<T>(zodSchema)` fuer strukturierte Page-Daten
- [ ] #6 `act(intent)` Compound API (observe -> resolve -> execute)
- [ ] #8 Vision-Fallback bei DOM-Confidence < 0.5

### Sprint 4 — IPC + DX (Woche 8–10) — **P1**
- [ ] #14 JSON-RPC Server ueber stdio (`unmask serve --stdio`)
- [ ] #15 HTTP+WebSocket Server (`unmask serve --http`)
- [ ] #16 `@unmask/schemas` als Cross-Language Shared Package
- [ ] #24 `unmask init` interaktiver Setup-Wizard
- [ ] #17 HACKING.md Python-Recipe (playstealth ↔ unmask)

### Sprint 5 — Production Ops (Woche 11–12) — **P2**
- [ ] #21 Telemetry: EUR/h Tracking + JSONL Export
- [ ] #23 Webhook + Console Alerts on Session Failure/Completion
- [ ] #41 Human-Input Realism (Mouse-Bezier #42, Typing #43)
- [ ] #46 Dockerfile + docker-compose
- [ ] #44 Webhook/Alert System (#45 PagerDuty)

### Ice-box
- #25 typedoc + mkdocs site
- #26 examples/ directory (consent-bypass, infinite-scroll, multi-tab)
- #38 HTTP-API (#39, #40)
- #35 Persona & Multi-Account Management

---

## 4. Definition of Done (DoD)

Pro Issue / PR:
- [ ] Code in `main`, kein offener Branch
- [ ] Unit-Tests + (wenn relevant) E2E-Tests gruen
- [ ] Coverage neuer Code >= 80 %
- [ ] Doku (README / HACKING) aktualisiert
- [ ] CHANGELOG-Eintrag
- [ ] Issue mit Commit + PR-Link geschlossen

---

## 5. Tech-Stack Decisions Log

| Datum | Entscheidung | Begruendung |
|---|---|---|
| 2026-04-28 | **Single-main-Branch-Policy** | Branch-Drift eliminieren |
| 2026-04-28 | **Forensic Replay als Hero-Feature** | Echter Differenzierer ggue. Browser-Use/Stagehand |
| 2026-04-28 | **LLM-Layer in Sprint 3 priorisieren** | Ohne `observe/extract/act` sind wir nur ein DOM-Scanner |
| 2026-04-28 | **Strict TS bleibt hart** | Verhindert ganze Bug-Klassen |

---

## 6. Companion-Stack — Sense + Act

```
+-------------------------------+         JSON-RPC         +--------------------------------+
|  unmask-cli  (TypeScript)     | <-----  stdio/http  ---> |  playstealth-cli  (Python)     |
|  ---------------------------  |                          |  ----------------------------  |
|  - CDP Network Sniffer        |                          |  - Stealth Browser Launcher    |
|  - DOM Semantic Scanner       |                          |  - Persona x Strategy Matrix   |
|  - Console Listener           |                          |  - Action Executor             |
|  - Forensic Replay (HAR/      |                          |  - Auto-Heal + Auto-Issue      |
|    trace/screenshots)         |                          |  - Survey Pacing Controller    |
|  - LLM observe/extract/act    |                          |                                |
|  -> emits structured events   |                          |  -> consumes events, acts      |
+-------------------------------+                          +--------------------------------+
        SENSE                                                       ACT
```

---

_Single Source of Truth. Aenderungen via PR auf diese Datei._
