# Implementation Order

Build in this order:

1. Bootstrap project
2. Database layer
3. Sample provider
4. Feature builder
5. Prediction engine
6. Value detector
7. Paper bet logger
8. Result settler
9. Evaluator
10. Full integration test

## Completed Tasks

- Task 01 - Bootstrap project
- Task 02 - Database layer
- Task 03 - Sample provider
- Task 04 - Core engine
- Task 05 - Settlement and evaluation
- Phase 8 - Football-Data public CSV import
- Phase 9 - Historical replay mode
- Task 06 - Football-Data multi-bookmaker odds
- Task 07 - Replay filters and report export
- Task 08 - Calibration and bet diagnostics
- Task 09 - Elo prediction engine
- Task 10 - Lightweight schema migrations
- Task 11 - Elo parameter configuration
- Task 12 - Replay comparison command
- Task 13 - Comparison workspace cleanup and metadata
- Task 14 - Comparison source cache
- Task 15 - Record model configuration in reports
- Task 16 - Comparison ranking
- Task 17 - Comparison temporary run databases
- Task 18 - Comparison parallel execution
- Task 19 - Staged model selection
- Task 20 - Configurable comparison workers
- Task 21 - Comparison analysis report
- Task 22 - Dashboard Data API
- Task 23 - Dashboard Scaffold
- Task 24 - Analytical Dashboard V1
- Task 25 - Dashboard QA
- Task 26 - Dashboard Bundle Optimization
- Task 27 - Database Identity Constraints
- Task 28 - Dashboard Report Catalog
- Task 29 - Dashboard Report Catalog Filter
- Task 30 - Dashboard Report Catalog Search
- Task 31 - Dashboard Run Drill-Down
- Task 32 - Dashboard Cross-Report Comparison
- Task 33 - Dashboard Cross-Report Trend
- Task 34 - Dashboard Calibration Trend
- Task 35 - Dashboard Trend Metric Controls
- Task 36 - Dashboard Selected-Run Insights
- Task 37 - Dashboard Generated Timestamp Ordering
- Misli.az Public Snapshot Discovery
- Task 38 - Live Provider Contract
- Task 39 - Live Run Registry
- Task 40 - Manual Live Collection Commands
- Task 41 - Live Paper Cycle Orchestrator
- Task 42 - Live Result Collection And Settlement Flow
- Task 43 - Live Process Status API
- Task 44 - Dashboard Process Monitor
- Task 45 - End-To-End Live Paper Dry Run
- Task 46 - Live Cycle Run Scoping
- Task 47 - Misli Kickoff Date Extraction
- Task 48 - AI-Assisted Analyst Layer, deterministic live and comparison analyst backbone
- Task 49 - Railway And Postgres Readiness
- Task 50 - Scheduled Paper Worker
- Task 53 - Misli Live Scraper Hardening
- Task 54 - Live Odds Movement Tracking
- Task 55 - Paper Bet Recommendation Engine
- Task 56 - Paper Bet Combination Engine
- Task 57 - AI Recommendation Review Layer
- Task 58 - Recommendation Dashboard
- Task 59 - Historical Recommendation Backtesting
- Task 51 - Railway Deployment Runbook And Production Smoke
- Task 60 - Railway Worker Deployment And Monitoring
- Task 61 - Operational Guardrails And Alerting
- Task 62 - Final Production Readiness Review
- Task 52 - Provider Health AI Analysis
- Task 63 - Railway API Config As Code
- Task 64 - Railway Dashboard Service
- Task 65 - Railway Scheduled Worker Service
- Task 66 - Daily Decision Dashboard Simplification
- Task 67 - Fresh Snapshot Worker Input
- Task 68 - Fresh Misli Snapshot Producer
- Task 69 - Misli Bare-Time Resolution
- Task 70 - Snapshot Producer Railway Image
- Planning - Live Misli recommendations and deployment readiness tasks 53 through 62 generated

## Current Next Task

The next implementation task is:

```text
Wait for or trigger the Railway worker to consume the fresh Misli snapshot, then prove the full fresh-data loop from producer to API to worker to dashboard.
```

Task 68 added and deployed the API latest-snapshot store, producer POST support, a browser-enabled `Dockerfile.snapshot`, and a scheduled `snapshot-producer` Railway service. The first fresh proof stored a 21-event Misli snapshot, but the worker failed on a bare `HH:MM` kickoff row. Task 69 fixes that parser gap and the API/worker deployment is healthy. Task 70 switched the producer to the official Playwright image because the previous Railway upload exported an image but stayed as a stopped `BUILDING` deployment; deployment `df944e43-9e2c-4bad-9b1f-0c582f4e5e37` is successful and a fresh snapshot was posted at `2026-05-28T00:05:28Z`. Task 70 also added service-specific Railway config references and removed root `railway.json` because it overrides every repo-linked service. A 2026-05-28 audit found fresh Misli recommendations were rejected as `missing_prediction`; the fix resolves bare-time scoping and adds neutral cold-start features for live teams without local history. The same follow-up rejects negative current-odds EV recommendations and counts in-run recommendation records in guardrails. New product work should prove the next scheduled worker cycle, then add richer club/player/stat sources. Do not add real-money execution, account automation, protected scraping, notification bots, or advanced ML before the paper-only live loop is automatically repeatable, monitored, and audited.

Required verification commands after implementation:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.api:api --reload
cd dashboard
npm run dev -- --host 127.0.0.1 --port 5173
npm run test
npm run snapshot:test
npm run lint
npm run build
npm run smoke
```

Expected result:

```text
New work preserves dashboard tests, smoke checks, and backend tests.
```

## Dashboard Phase Order

Build dashboard work in this order:

1. Task 22 - Dashboard Data API
2. Task 23 - Dashboard Scaffold
3. Task 24 - Analytical Dashboard V1
4. Task 25 - Dashboard QA
5. Task 26 - Dashboard Bundle Optimization
6. Task 28 - Dashboard Report Catalog
7. Task 29 - Dashboard Report Catalog Filter
8. Task 30 - Dashboard Report Catalog Search
9. Task 31 - Dashboard Run Drill-Down
10. Task 32 - Dashboard Cross-Report Comparison
11. Task 33 - Dashboard Cross-Report Trend
12. Task 34 - Dashboard Calibration Trend
13. Task 35 - Dashboard Trend Metric Controls
14. Task 36 - Dashboard Selected-Run Insights
15. Task 37 - Dashboard Generated Timestamp Ordering

## Live Paper Phase Order

Build the paper-only live loop in this order:

1. Task 38 - Live Provider Contract, including Misli public snapshot DTOs and validation
2. Task 39 - Live Run Registry
3. Task 40 - Manual Live Collection Commands, including validated Misli snapshot import or documented fallback
4. Task 41 - Live Paper Cycle Orchestrator
5. Task 42 - Live Result Collection And Settlement Flow
6. Task 43 - Live Process Status API
7. Task 44 - Dashboard Process Monitor
8. Task 45 - End-To-End Live Paper Dry Run, preferring Misli public snapshot when validation is complete
9. Task 46 - Live Cycle Run Scoping, completed
10. Task 47 - Misli Kickoff Date Extraction, relative labels completed and bare time-only rows fail closed
11. Task 48 - AI-Assisted Analyst Layer, deterministic live and comparison analyst backbone completed
12. Task 52 - Provider Health AI Analysis, completed
13. Task 49 - Railway And Postgres Readiness, completed
14. Task 50 - Scheduled Paper Worker, completed
15. Task 53 - Misli Live Scraper Hardening, completed
16. Task 54 - Live Odds Movement Tracking, completed
17. Task 55 - Paper Bet Recommendation Engine, completed
18. Task 56 - Paper Bet Combination Engine, completed
19. Task 57 - AI Recommendation Review Layer, completed
20. Task 58 - Recommendation Dashboard, completed
21. Task 59 - Historical Recommendation Backtesting, completed
22. Task 51 - Railway Deployment Runbook And Production Smoke, completed
23. Task 60 - Railway Worker Deployment And Monitoring, completed
24. Task 61 - Operational Guardrails And Alerting, completed
25. Task 62 - Final Production Readiness Review, completed
26. Task 66 - Daily Decision Dashboard Simplification, completed
27. Task 67 - Fresh Snapshot Worker Input, completed

## AI-Assisted Product Phase Order

The current system has statistical prediction models and deterministic analytical summaries. It does not yet have an explicit LLM/agentic assistant inside the product. The target AI architecture is documented in:

```text
docs/specs/ai-assisted-backbone.md
```

Build AI assistance in this order:

1. Implemented: Task 48 deterministic AI analyst persistence, API, CLI, and dashboard panel.
2. Implemented: Task 48 prompt/version registry, provider boundary, AI analysis config defaults, and fail-closed eval gates.
3. Implemented: Task 48 comparison-report analyst mode through `analyze-comparison-ai`.
4. Implemented: Task 52 provider-health analyst mode through `analyze-provider-health`.
5. Implemented: Task 57 recommendation and combination AI review mode through `analyze-recommendations`.
6. Implemented: Task 59 recommendation backtest analyst mode through `analyze-recommendation-backtest`.
7. Later: optional LLM-backed analysis provider using official OpenAI docs and secure credential handling.
8. Later: richer AI-assisted experiment design over historical replay/comparison results.
9. Later: deployment readiness analyst mode.

AI assistance must remain advisory and paper-only. It must not place bets, automate accounts, or override safety rules.

## Deployment Phase Order

Build Railway readiness in this order:

1. Task 49 - Railway And Postgres Readiness
2. Task 50 - Scheduled Paper Worker
3. Task 51 - Railway Deployment Runbook And Production Smoke, completed
4. Task 60 - Railway Worker Deployment And Monitoring, completed
5. Task 61 - Operational Guardrails And Alerting, completed
6. Task 62 - Final Production Readiness Review, completed
7. Task 63 - Railway API Config As Code, completed
8. Task 64 - Railway Dashboard Service, completed
9. Task 65 - Railway Scheduled Worker Service, completed
10. Task 66 - Daily Decision Dashboard Simplification, completed
11. Task 67 - Fresh Snapshot Worker Input, completed

## Recommendation Phase Order

Build live recommendation work in this order:

1. Task 53 - Misli Live Scraper Hardening
2. Task 54 - Live Odds Movement Tracking
3. Task 55 - Paper Bet Recommendation Engine
4. Task 56 - Paper Bet Combination Engine, completed
5. Task 57 - AI Recommendation Review Layer, completed
6. Task 58 - Recommendation Dashboard, completed
7. Task 59 - Historical Recommendation Backtesting, completed
8. Task 66 - Daily Decision Dashboard Simplification, completed
9. Task 67 - Fresh Snapshot Worker Input, completed
10. Task 71 - Recommendation Quality Cycle Report, completed
11. Task 72 - Raw Versus Calibrated Recommendation Confidence, completed
12. Task 73 - Confidence Calibration Backtest Scenarios, completed
13. Task 74 - Richer Team Strength Feature Inputs
14. Task 75 - Daily Paper Trading Journal
15. Task 76 - Combination Risk Quarantine
16. Task 77 - Outcome Learning And Threshold Review Loop

## Recommendation Maturity Phase Order

The live paper loop is operationally healthy, but the model and review layer are still early. Build maturity in this order:

1. Implemented: Task 71 makes every worker cycle auditable through one quality report.
2. Implemented: Task 72 separates raw model confidence from calibrated recommendation confidence.
3. Implemented: Task 73 compares raw and calibrated confidence scenarios in recommendation backtests and makes the AI summary give a provisional keep/disable calibration decision.
4. Task 74 - add richer team-strength and match-context features.
5. Task 75 - create a daily paper trading journal so decisions become a learning record.
6. Task 76 - keep combinations quarantined until correlation and exposure risk are better modeled.
7. Task 77 - turn settled outcomes into conservative threshold review advice.

## Do Not Jump Ahead

Do not implement real-money betting, bookmaker account automation, protected scraping, notification bots, or advanced ML before the paper-only live loop is automatically repeatable, monitored, and audited.
