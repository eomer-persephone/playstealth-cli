# unmask-cli — ROADMAP

> Lebendes Dokument, gepaart mit [PLAN.md](./PLAN.md). Sub-Issues sind verlinkt.

## Now (Sprint 1) — P0 Stabilisierung
- #18 postinstall hook playwright install
- #19 `unmask doctor` self-diagnostic
- #20 Self-healing Resolver in QueueManager
- #22 Real-Browser E2E Test
- NEU: Coverage-Gate >= 75 % in CI

## Next (Sprint 2) — P0 Forensic Replay
- #9 HAR-Export pro Session
- #10 Playwright trace.zip pro Session
- #11 Screenshot-Timeline
- #12 Single-Zip Bundle Exporter

## Then (Sprint 3) — P0/P1 LLM Reasoning
- #7 DOM-Tree-to-LLM Serializer
- #4 `observe(intent)` API
- #5 `extract<T>(zodSchema)` API
- #6 `act(intent)` Compound API
- #8 Vision-Fallback bei DOM-Confidence < 0.5

## Later (Sprint 4) — P1 IPC + DX
- #14 JSON-RPC ueber stdio
- #15 HTTP+WebSocket Server
- #16 `@unmask/schemas` Shared Package
- #17 HACKING Python-Recipe
- #24 `unmask init` Wizard

## Production (Sprint 5) — P2 Ops
- #21 Telemetry EUR/h + JSONL
- #23 Webhook + Console Alerts
- #41 Human-Input Realism (#42 #43)
- #44 Webhook/Alert System (#45)
- #46 Dockerfile + docker-compose

## Ice-box
- #25 typedoc + mkdocs site
- #26 examples/ directory
- #35 Persona + Multi-Account
- #38 HTTP-API (#39 #40)
