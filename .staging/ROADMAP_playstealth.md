# playstealth-cli — ROADMAP

> Lebendes Dokument, gepaart mit [PLAN.md](./PLAN.md). Issues sind Pflicht-Verlinkung.

## Now (Sprint 1) — Stabilisierung
- demo-Bug, Sprach-EN, Versions-Hygiene
- REOPEN #11, Tests fuer Resilience-Module
- Security-Cleanup #9 (Key rotieren + History)

## Next (Sprint 2) — Beweis
- CreepJS / SannySoft Benchmark in CI mit Score-Gate
- Coverage-Gate >= 75 %
- `playstealth init` Wizard
- Performance-Benchmark-Suite
- PyPI-Release

## Later (Sprint 3) — Pivot
- Plugin-Ausgliederung (hey_piggy, qualtrics)
- Rebrand Core -> Stealth + QA-Test
- Demo-Video, Blogpost, Landingpage
- Vergleichsmatrix vs Stagehand / Browser-Use / Skyvern

## Then (Sprint 4) — Wachstum
- Patchright-Migration
- JSON-RPC zu unmask-cli
- CAPTCHA-Adapter
- DX (--version, completion, error-codes)

## Ice-box
- i18n-Layer (DE/EN)
- Multi-Browser-Profile (Firefox/WebKit)
- Headed-Mode-Recorder

---

```
[CEO Audit 2026-04-28]
        │
        ▼
[Sprint 1 Stabilisierung] -> [Sprint 2 Beweis] -> [Sprint 3 Pivot] -> [Sprint 4 Wachstum]
   demo-fix                    CreepJS-CI            Plugin-Split        Patchright
   sprach-EN                   Coverage-Gate         Marketing           JSON-RPC
   key-rotation                init-Wizard           Vergleichsmatrix    CAPTCHA
   reopen #11                  PyPI-Release          Demo-Video          Community
```
