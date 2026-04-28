# playstealth-cli — Master PLAN (Single Source of Truth)

> **Status:** Beta · v1.0.0 (lokal, NICHT auf PyPI) · main = Source of Truth
> **Owner:** SIN-CLIs/playstealth-cli
> **Letztes Audit:** 2026-04-28 (CEO Review)
> **Companion-Repo:** [SIN-CLIs/unmask-cli](https://github.com/SIN-CLIs/unmask-cli)

---

## 0. Working Agreement (verbindlich)

1. **Single-Branch-Policy** — alle Arbeit landet auf `main`. Feature-Branches sind kurzlebig (≤ 48 h) und werden nach Merge sofort gelöscht.
2. **No half-done issues** — ein Issue wird erst geschlossen, wenn (a) Code in `main`, (b) Tests grün, (c) Doku aktualisiert. Sonst Reopen mit Begründung.
3. **CI = Gate** — kein Merge ohne grüne CI (lint, type, test, security).
4. **Security-First** — Keine Secrets im Repo, Pre-Commit-Gitleaks pflicht.
5. **Sprache** — Code, Doku, CLI-Output: **Englisch**. Optionaler i18n-Layer kommt später.

---

## 1. Audit-Befunde (CEO Review 2026-04-28)

### Halbherzig geschlossene Issues
| Issue | Status | Befund |
|---|---|---|
| #11 Resilience Engine v1.0 | CLOSED/COMPLETED | Code vorhanden, aber **Tests leer**: `test_resilience_config.py`, `test_github_issue_reporter.py`, `test_auto_heal_selector.py`, `test_secret_manager.py` enthalten **0 Test-Funktionen** -> **REOPEN als Test-Coverage-Gap**. |
| #12 Test-Issue Auto-Report | CLOSED/COMPLETED | War nur Validierungs-Trigger, OK. |

### Kritische offene Punkte
- **#9** geleakter NVIDIA-API-Key in `.env` (Commit `bb966f8`) — **noch nicht rotiert / nicht aus History entfernt**.
- **PR #30** (`v0/infoplay2015-1241-af8b70e7`): 22 Commits hinter main, `CONFLICTING/DIRTY` -> **schliessen, nicht mergen**.
- **demo-Bug**: `from demo_flow import run_demo` als Top-Level-Import bricht nach pipx-Install.
- **PyPI-Badge** im README zeigt ins Leere — Version 1.0.0 ist nicht released.
- **Sprach-Mix** in CLI-Strings (DE/EN).
- **4 leere Test-Dateien** unter `tests/` (siehe oben).

---

## 2. Strategische Positionierung

**Wettbewerb:** `playwright-stealth`, `undetected-chromedriver`, `playwright-extra`, `nodriver`, `botright`, `camoufox`, `patchright`.

**Unser USP** (was wir wirklich verkaufen sollten):
1. **Self-Healing-Pipeline** (Auto-Heal-Selector + Auto-Issue + Auto-PR via GitHub App).
2. **Survey-Vertical-Profiler** (Plugin-Scaffolder aus Live-DOM-Profiling).
3. **Persona x Strategy Matrix** für deterministische, reproduzierbare Antwortlogik.

**Nicht** unser USP: "Stealth" allein — das ist Commodity.

**Pivot-Empfehlung:** Plattform-spezifische Plugins (`hey_piggy.py`, `qualtrics.py`) aus Core ausgliedern in separates Repo. Core wird zu einem **neutralen Stealth + QA-Test-Framework**.

---

## 3. 90-Tage-Roadmap

### Sprint 1 — Stabilisierung (Woche 1–2)
- [ ] `demo`-Bug fixen (Top-Level-Import -> relativer Import)
- [ ] Sprach-Vereinheitlichung (alle CLI-Strings -> EN)
- [ ] Pre-Flight-Check aufweichen (`--no-preflight` Flag)
- [ ] Versions-Hygiene: PyPI-Release v1.0.0 ODER Version auf `0.9.0-beta`
- [ ] **REOPEN #11** und Tests fuer Resilience-Module schreiben
- [ ] Secret-History-Cleanup fuer #9 (BFG / git-filter-repo) + Key rotieren

### Sprint 2 — Beweis (Woche 3–4)
- [ ] CreepJS / SannySoft Benchmark-CI-Job mit Score-Artefakt + Mindest-Threshold
- [ ] Coverage-Gate >= 75 % in CI (pytest-cov)
- [ ] `playstealth init` Wizard (Env-Setup, Plugin-Auswahl, Stealth-Profile-Validierung)
- [ ] Performance-Benchmark-Suite (Surveys/h, RAM, Browser-Lifetime) als README-Tabelle
- [ ] PyPI-Release ausfuehren

### Sprint 3 — Pivot (Woche 5–7)
- [ ] Plattform-Plugins (`hey_piggy.py`, `qualtrics.py`) in separates Repo `playstealth-vertical-plugins`
- [ ] Core wird neutrales Framework, README rebranded auf "Stealth + QA-Test"
- [ ] Auto-Heal-Demo-Video + Blogpost (Hero-Marketing)
- [ ] Vergleichs-Matrix gegen Stagehand / Browser-Use / Skyvern (siehe #26)

### Sprint 4 — Wachstum (Woche 8–12)
- [ ] `--version`, Shell-Completion (bash/zsh/fish), strukturierte Error-Codes (`PSE-XXXX`)
- [ ] HTTP-API / JSON-RPC Bridge zu unmask-cli (siehe #21–#23)
- [ ] CAPTCHA-Adapter (#27–#29)
- [ ] Patchright-Migration (#17–#20)
- [ ] Community-Outreach (HN, Reddit r/Python, dev.to)

---

## 4. Definition of Done (DoD)

Ein Feature gilt erst dann als **fertig**, wenn:

- [ ] Code in `main`, kein offener Branch dazu
- [ ] Unit-Tests + Integration-Tests vorhanden, alle gruen in CI
- [ ] Coverage des neuen Codes >= 80 %
- [ ] Doku aktualisiert (README, HACKING, COMPLIANCE wenn relevant)
- [ ] CHANGELOG-Eintrag vorhanden
- [ ] Manuell auf reproduzierbarem Demo-Run validiert
- [ ] Issue mit Commit-Hash + PR-Nummer geschlossen

---

## 5. Verlinkte Issues (Master-Index)

**Epics (offen):**
- #17 Replace playwright with patchright
- #21 Integration unmask-cli ↔ playstealth-cli (JSON-RPC)
- #24 README + architecture documentation
- #27 CAPTCHA + Rate-Limit Handling

**Neue Issues aus diesem Audit** werden nach Erstellung am Ende dieser Datei verlinkt.

---

## 6. Tech-Stack Decisions Log (ADR-light)

| Datum | Entscheidung | Begruendung |
|---|---|---|
| 2026-04-28 | **Single-main-Branch-Policy** | Eliminiert Branch-Drift, Konflikte, halbe Implementationen |
| 2026-04-28 | **Patchright statt Playwright** (geplant, #17) | Stealth out-of-the-box, weniger eigener Patch-Code |
| 2026-04-28 | **Vertical-Plugins ausgliedern** | Reputation/Compliance-Risiko reduzieren |
| 2026-04-28 | **CreepJS-Score als CI-Gate** | Stealth-Versprechen muss messbar sein |

---

_Dieses Dokument ist die Single Source of Truth. Aenderungen am Plan = PR auf diese Datei._
