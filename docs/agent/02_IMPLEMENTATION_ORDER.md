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
- Task 52 - Provider Health AI Analysis
- Planning - Live Misli recommendations and deployment readiness tasks 53 through 62 generated

## Current Next Task

The next implementation task is:

```text
Task 58 - Recommendation Dashboard
```

Task 57 added AI-assisted advisory review for paper recommendations and combinations. Do not add real-money execution, account automation, or protected scraping while building the recommendation dashboard.

Required verification commands after implementation:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.api:api --reload
cd dashboard
npm run dev -- --host 127.0.0.1 --port 5173
npm run test
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
20. Task 58 - Recommendation Dashboard
21. Task 59 - Historical Recommendation Backtesting
22. Task 51 - Railway Deployment Runbook And Production Smoke
23. Task 60 - Railway Worker Deployment And Monitoring
24. Task 61 - Operational Guardrails And Alerting
25. Task 62 - Final Production Readiness Review

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
6. Later: optional LLM-backed analysis provider using official OpenAI docs and secure credential handling.
7. Later: richer AI-assisted experiment design over historical replay/comparison results.
8. Later: deployment readiness analyst mode.

AI assistance must remain advisory and paper-only. It must not place bets, automate accounts, or override safety rules.

## Deployment Phase Order

Build Railway readiness in this order:

1. Task 49 - Railway And Postgres Readiness
2. Task 50 - Scheduled Paper Worker
3. Task 51 - Railway Deployment Runbook And Production Smoke
4. Task 60 - Railway Worker Deployment And Monitoring
5. Task 61 - Operational Guardrails And Alerting
6. Task 62 - Final Production Readiness Review

## Recommendation Phase Order

Build live recommendation work in this order:

1. Task 53 - Misli Live Scraper Hardening
2. Task 54 - Live Odds Movement Tracking
3. Task 55 - Paper Bet Recommendation Engine
4. Task 56 - Paper Bet Combination Engine, completed
5. Task 57 - AI Recommendation Review Layer, completed
6. Task 58 - Recommendation Dashboard
7. Task 59 - Historical Recommendation Backtesting

## Do Not Jump Ahead

Do not implement real-money betting, bookmaker account automation, protected scraping, notification bots, or advanced ML before the paper-only live loop is automatically repeatable, monitored, and audited.
