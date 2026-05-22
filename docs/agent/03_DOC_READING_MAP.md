# Doc Reading Map

Read `AGENTS.md` first, then this file. Load only the docs needed for the current task.

## Required Completion Updates

After each implementation task, update:

- `docs/agent/02_IMPLEMENTATION_ORDER.md`
- the relevant task doc under `docs/tasks/`
- this reading map if new workflows or docs were introduced
- `docs/agent/04_OPEN_QUESTIONS.md` if decisions or ambiguities changed
- `docs/agent/05_TECHNICAL_DEBT.md` if technical debt changed
- relevant specs under `docs/specs/` if behavior changed

Then run the full test suite and full lint check before reporting completion.

Focused tests are not enough for final completion.

Required full verification:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

## Required Completion Report

Every implementation completion message should include:

- what was done
- what is next
- blockers
- technical debt or known limitations

Read `docs/agent/05_TECHNICAL_DEBT.md` before planning work that may touch known debt areas.

## Always Read

- `docs/agent/00_READ_ME_FIRST.md`
- `docs/agent/01_RULES_AND_BOUNDARIES.md`
- `docs/agent/04_OPEN_QUESTIONS.md`

## Task 01 - Bootstrap

- `docs/tasks/task-01-bootstrap.md`
- `docs/specs/configuration.md`
- `docs/specs/testing-strategy.md`

## Task 02 - Database Layer

- `docs/tasks/task-02-database.md`
- `docs/specs/database-schema.md`
- `docs/specs/configuration.md`
- `docs/specs/logging-and-evaluation.md`

## Task 03 - Sample Provider

- `docs/tasks/task-03-sample-provider.md`
- `docs/specs/data-providers.md`
- `docs/specs/pipeline-flow.md`
- `docs/specs/database-schema.md`

## Task 04 - Core Engine

- `docs/tasks/task-04-core-engine.md`
- `docs/specs/feature-engineering.md`
- `docs/specs/prediction-engine.md`
- `docs/specs/value-detection-and-paper-bets.md`
- `docs/specs/testing-strategy.md`

## Task 05 - Settlement And Evaluation

- `docs/tasks/task-05-settlement-evaluation.md`
- `docs/specs/value-detection-and-paper-bets.md`
- `docs/specs/logging-and-evaluation.md`
- `docs/specs/testing-strategy.md`

## Future Providers

Only after the offline sample pipeline works:

- `docs/specs/data-providers.md`
- `docs/specs/live-paper-loop.md`
- `docs/specs/pipeline-flow.md`
- `docs/specs/safety-and-compliance.md`

## Task 06 - Football-Data Multi-Bookmaker Odds

- `docs/tasks/task-06-football-data-multi-bookmaker.md`
- `docs/specs/data-providers.md`
- `docs/specs/database-schema.md`
- `docs/specs/value-detection-and-paper-bets.md`
- `docs/specs/testing-strategy.md`

## Task 07 - Replay Filters And Report Export

- `docs/tasks/task-07-replay-filters-report-export.md`
- `docs/specs/pipeline-flow.md`
- `docs/specs/logging-and-evaluation.md`
- `docs/specs/testing-strategy.md`

## Task 08 - Calibration And Bet Diagnostics

- `docs/tasks/task-08-calibration-bet-diagnostics.md`
- `docs/specs/logging-and-evaluation.md`
- `docs/specs/testing-strategy.md`

## Task 09 - Elo Prediction Engine

- `docs/tasks/task-09-elo-prediction-engine.md`
- `docs/specs/prediction-engine.md`
- `docs/specs/feature-engineering.md`
- `docs/specs/testing-strategy.md`

## Task 10 - Lightweight Schema Migrations

- `docs/tasks/task-10-lightweight-schema-migrations.md`
- `docs/specs/database-schema.md`
- `docs/specs/testing-strategy.md`

## Task 11 - Elo Parameter Configuration

- `docs/tasks/task-11-elo-parameter-configuration.md`
- `docs/specs/configuration.md`
- `docs/specs/prediction-engine.md`
- `docs/specs/testing-strategy.md`

## Task 12 - Replay Comparison Command

- `docs/tasks/task-12-replay-comparison-command.md`
- `docs/specs/pipeline-flow.md`
- `docs/specs/logging-and-evaluation.md`
- `docs/specs/testing-strategy.md`

## Task 13 - Comparison Workspace Cleanup And Metadata

- `docs/tasks/task-13-comparison-workspace-cleanup.md`
- `docs/tasks/task-12-replay-comparison-command.md`
- `docs/specs/pipeline-flow.md`
- `docs/specs/logging-and-evaluation.md`

## Task 14 - Comparison Source Cache

- `docs/tasks/task-14-comparison-source-cache.md`
- `docs/tasks/task-13-comparison-workspace-cleanup.md`
- `docs/tasks/task-12-replay-comparison-command.md`
- `docs/specs/pipeline-flow.md`

## Task 15 - Record Model Configuration In Reports

- `docs/tasks/task-15-record-model-configuration.md`
- `docs/specs/logging-and-evaluation.md`
- `docs/specs/configuration.md`
- `docs/agent/05_TECHNICAL_DEBT.md`

## Task 16 - Comparison Ranking

- `docs/tasks/task-16-comparison-ranking.md`
- `docs/tasks/task-12-replay-comparison-command.md`
- `docs/specs/logging-and-evaluation.md`

## Task 17 - Comparison Temporary Run Databases

- `docs/tasks/task-17-comparison-temp-run-dbs.md`
- `docs/tasks/task-13-comparison-workspace-cleanup.md`
- `docs/tasks/task-14-comparison-source-cache.md`
- `docs/agent/05_TECHNICAL_DEBT.md`

## Task 18 - Comparison Parallel Execution

- `docs/tasks/task-18-comparison-parallel-execution.md`
- `docs/tasks/task-12-replay-comparison-command.md`
- `docs/tasks/task-17-comparison-temp-run-dbs.md`
- `docs/specs/pipeline-flow.md`
- `docs/agent/05_TECHNICAL_DEBT.md`

## Task 19 - Staged Model Selection

- `docs/tasks/task-19-staged-model-selection.md`
- `docs/tasks/task-09-elo-prediction-engine.md`
- `docs/specs/configuration.md`
- `docs/specs/pipeline-flow.md`
- `docs/agent/05_TECHNICAL_DEBT.md`

## Task 20 - Configurable Comparison Workers

- `docs/tasks/task-20-configurable-comparison-workers.md`
- `docs/tasks/task-18-comparison-parallel-execution.md`
- `docs/specs/pipeline-flow.md`
- `docs/agent/05_TECHNICAL_DEBT.md`

## Task 21 - Comparison Analysis Report

- `docs/superpowers/specs/2026-05-18-analysis-reports-design.md`
- `docs/tasks/task-21-comparison-analysis-report.md`
- `docs/specs/logging-and-evaluation.md`
- `docs/tasks/task-12-replay-comparison-command.md`
- `docs/agent/05_TECHNICAL_DEBT.md`

## Dashboard Phase

- `docs/decisions/ADR-0003-dashboard-stack.md`
- `docs/specs/dashboard.md`
- `docs/specs/architecture.md`
- `docs/specs/configuration.md`
- `docs/specs/safety-and-compliance.md`

## Live Paper Phase

- `docs/specs/live-paper-loop.md`
- `docs/specs/data-providers.md`
- `docs/research/misli-public-discovery.md`
- `docs/specs/pipeline-flow.md`
- `docs/specs/logging-and-evaluation.md`
- `docs/specs/database-schema.md`
- `docs/specs/safety-and-compliance.md`
- `docs/agent/04_OPEN_QUESTIONS.md`
- `docs/agent/05_TECHNICAL_DEBT.md`

## Task 38 - Live Provider Contract

- `docs/tasks/task-38-live-provider-contract.md`
- `docs/research/misli-public-discovery.md`
- `docs/specs/live-paper-loop.md`
- `docs/specs/data-providers.md`
- `docs/specs/safety-and-compliance.md`

## Task 39 - Live Run Registry

- `docs/tasks/task-39-live-run-registry.md`
- `docs/specs/live-paper-loop.md`
- `docs/specs/database-schema.md`
- `docs/specs/logging-and-evaluation.md`
- `docs/agent/05_TECHNICAL_DEBT.md`

## Task 40 - Manual Live Collection Commands

- `docs/tasks/task-40-manual-live-collection-commands.md`
- `docs/tasks/task-38-live-provider-contract.md`
- `docs/tasks/task-39-live-run-registry.md`
- `docs/specs/live-paper-loop.md`
- `docs/specs/data-providers.md`
- `docs/specs/pipeline-flow.md`

## Task 41 - Live Paper Cycle Orchestrator

- `docs/tasks/task-41-live-paper-cycle-orchestrator.md`
- `docs/tasks/task-39-live-run-registry.md`
- `docs/tasks/task-40-manual-live-collection-commands.md`
- `docs/specs/live-paper-loop.md`
- `docs/specs/pipeline-flow.md`
- `docs/specs/value-detection-and-paper-bets.md`

## Task 42 - Live Result Collection And Settlement Flow

- `docs/tasks/task-42-live-result-collection-settlement.md`
- `docs/tasks/task-39-live-run-registry.md`
- `docs/specs/live-paper-loop.md`
- `docs/specs/data-providers.md`
- `docs/specs/logging-and-evaluation.md`

## Task 43 - Live Process Status API

- `docs/tasks/task-43-live-process-status-api.md`
- `docs/tasks/task-39-live-run-registry.md`
- `docs/specs/live-paper-loop.md`
- `docs/specs/dashboard.md`

## Task 44 - Dashboard Process Monitor

- `docs/tasks/task-44-dashboard-process-monitor.md`
- `docs/tasks/task-43-live-process-status-api.md`
- `docs/specs/live-paper-loop.md`
- `docs/specs/dashboard.md`
- `docs/decisions/ADR-0003-dashboard-stack.md`

## Task 45 - End-To-End Live Paper Dry Run

- `docs/tasks/task-45-end-to-end-live-paper-dry-run.md`
- `docs/fixtures/task45-live-dry-run-snapshot.json`
- `docs/fixtures/task45-live-dry-run-results.json`
- `docs/specs/live-paper-loop.md`
- `docs/specs/pipeline-flow.md`
- `docs/specs/dashboard.md`
- `docs/specs/testing-strategy.md`

## Task 46 - Live Cycle Run Scoping

- `docs/tasks/task-45-end-to-end-live-paper-dry-run.md`
- `docs/tasks/task-46-live-cycle-run-scoping.md`
- `docs/specs/live-paper-loop.md`
- `docs/agent/05_TECHNICAL_DEBT.md`
- `app/services/live_cycle_service.py`

## Task 47 - Misli Kickoff Date Extraction

- `docs/tasks/task-47-misli-kickoff-date-extraction.md`
- `docs/research/misli-public-discovery.md`
- `docs/specs/live-paper-loop.md`
- `docs/specs/safety-and-compliance.md`
- `tools/misli-public-snapshot.mjs`
- `app/providers/misli_public.py`

## Task 48 - AI-Assisted Analyst Layer

- `docs/tasks/task-48-ai-assisted-analyst-layer.md`
- `docs/specs/ai-assisted-backbone.md`
- `docs/specs/dashboard.md`
- `docs/specs/logging-and-evaluation.md`
- `docs/specs/safety-and-compliance.md`
- `app/services/ai_analysis_service.py`
- `app/services/ai_prompt_registry.py`
- `app/services/ai_analysis_evals.py`
- `app/services/analysis_service.py`

## Task 52 - Provider Health AI Analysis

- `docs/tasks/task-52-provider-health-ai-analysis.md`
- `docs/specs/ai-assisted-backbone.md`
- `docs/specs/live-paper-loop.md`
- `docs/agent/05_TECHNICAL_DEBT.md`
- `app/services/ai_analysis_service.py`
- `app/services/ai_prompt_registry.py`
- `app/services/live_status_service.py`

## Task 49 - Railway And Postgres Readiness

- `docs/tasks/task-49-railway-postgres-readiness.md`
- `docs/deployment/railway-readiness.md`
- `docs/specs/configuration.md`
- `docs/specs/database-schema.md`
- `docs/specs/testing-strategy.md`
- `.env.example`
- `app/api.py`
- `app/db/migrations.py`
- `dashboard/src/lib/api.ts`

## Task 50 - Scheduled Paper Worker

- `docs/tasks/task-50-scheduled-paper-worker.md`
- `docs/tasks/task-46-live-cycle-run-scoping.md`
- `docs/specs/live-paper-loop.md`
- `docs/specs/safety-and-compliance.md`
- `docs/specs/configuration.md`
- `app/services/scheduled_worker_service.py`
- `app/services/live_cycle_service.py`
- `app/cli.py`

## Task 51 - Railway Deployment Runbook And Production Smoke

- `docs/tasks/task-51-railway-deployment-runbook.md`
- `docs/tasks/task-49-railway-postgres-readiness.md`
- `docs/tasks/task-50-scheduled-paper-worker.md`
- `docs/specs/configuration.md`
- `docs/specs/testing-strategy.md`

## Live Misli Recommendation Plan

- `docs/superpowers/plans/2026-05-22-live-misli-recommendations.md`
- `docs/specs/live-paper-loop.md`
- `docs/specs/ai-assisted-backbone.md`
- `docs/specs/dashboard.md`
- `docs/specs/safety-and-compliance.md`

## Task 53 - Misli Live Scraper Hardening

- `docs/tasks/task-53-misli-live-scraper-hardening.md`
- `docs/research/misli-public-discovery.md`
- `docs/specs/data-providers.md`
- `docs/specs/live-paper-loop.md`
- `docs/specs/safety-and-compliance.md`
- `tools/misli-public-snapshot.mjs`
- `app/providers/misli_public.py`

## Task 54 - Live Odds Movement Tracking

- `docs/tasks/task-54-live-odds-movement-tracking.md`
- `docs/specs/database-schema.md`
- `docs/specs/live-paper-loop.md`
- `docs/specs/logging-and-evaluation.md`
- `docs/specs/dashboard.md`
- `app/services/odds_movement_service.py`
- `app/services/live_collection_service.py`
- `app/api.py`
- `dashboard/src/lib/api.ts`
- `app/db/models.py`
- `app/db/repositories.py`

## Task 55 - Paper Bet Recommendation Engine

- `docs/tasks/task-55-paper-bet-recommendation-engine.md`
- `docs/specs/value-detection-and-paper-bets.md`
- `docs/specs/prediction-engine.md`
- `docs/specs/ai-assisted-backbone.md`
- `docs/specs/database-schema.md`
- `app/services/recommendation_service.py`
- `app/services/odds_movement_service.py`
- `app/db/models.py`
- `app/db/migrations.py`
- `app/api.py`
- `app/cli.py`
- `app/services/prediction_service.py`
- `app/core/value_detector.py`

## Task 56 - Paper Bet Combination Engine

- `docs/tasks/task-56-paper-bet-combination-engine.md`
- `docs/specs/value-detection-and-paper-bets.md`
- `docs/specs/database-schema.md`
- `docs/specs/dashboard.md`
- `docs/specs/safety-and-compliance.md`
- `docs/agent/05_TECHNICAL_DEBT.md`
- `app/services/combination_service.py`
- `app/db/models.py`
- `app/db/migrations.py`
- `app/api.py`
- `app/cli.py`
- `dashboard/src/lib/api.ts`

## Task 57 - AI Recommendation Review Layer

- `docs/tasks/task-57-ai-recommendation-review-layer.md`
- `docs/specs/ai-assisted-backbone.md`
- `docs/specs/safety-and-compliance.md`
- `app/services/ai_analysis_service.py`
- `app/services/ai_prompt_registry.py`
- `app/services/ai_analysis_evals.py`

## Task 58 - Recommendation Dashboard

- `docs/tasks/task-58-recommendation-dashboard.md`
- `docs/specs/dashboard.md`
- `docs/decisions/ADR-0003-dashboard-stack.md`
- `dashboard/src/App.tsx`
- `dashboard/src/lib/api.ts`

## Task 59 - Historical Recommendation Backtesting

- `docs/tasks/task-59-historical-recommendation-backtesting.md`
- `docs/specs/logging-and-evaluation.md`
- `docs/specs/pipeline-flow.md`
- `docs/specs/ai-assisted-backbone.md`

## Task 60 - Railway Worker Deployment And Monitoring

- `docs/tasks/task-60-railway-worker-deployment-monitoring.md`
- `docs/deployment/railway-readiness.md`
- `.env.example`
- `docs/specs/configuration.md`

## Task 61 - Operational Guardrails And Alerting

- `docs/tasks/task-61-operational-guardrails-alerting.md`
- `docs/specs/live-paper-loop.md`
- `docs/specs/dashboard.md`
- `docs/agent/04_OPEN_QUESTIONS.md`

## Task 62 - Final Production Readiness Review

- `docs/tasks/task-62-final-production-readiness-review.md`
- `docs/agent/05_TECHNICAL_DEBT.md`
- `docs/agent/04_OPEN_QUESTIONS.md`
- `docs/deployment/railway-readiness.md`

## Task 22 - Dashboard Data API

- `docs/tasks/task-22-dashboard-data-api.md`
- `docs/specs/dashboard.md`
- `docs/specs/logging-and-evaluation.md`
- `docs/decisions/ADR-0003-dashboard-stack.md`

## Task 23 - Dashboard Scaffold

- `docs/tasks/task-23-dashboard-scaffold.md`
- `docs/specs/dashboard.md`
- `docs/decisions/ADR-0003-dashboard-stack.md`
- `docs/specs/safety-and-compliance.md`

## Task 24 - Analytical Dashboard V1

- `docs/tasks/task-24-analytical-dashboard-v1.md`
- `docs/specs/dashboard.md`
- `docs/decisions/ADR-0003-dashboard-stack.md`
- `docs/specs/logging-and-evaluation.md`

## Task 25 - Dashboard QA

- `docs/tasks/task-25-dashboard-qa.md`
- `docs/specs/dashboard.md`
- `docs/decisions/ADR-0003-dashboard-stack.md`

## Plugin Guidance

- Use Superpowers process skills for planning, TDD, debugging, and verification.
- Use GitHub only after this folder is initialized as a Git repository or connected to a remote.
- Use Spreadsheets for CSV imports, exports, or spreadsheet report work.
- Use Browser or Build Web Apps only when a web dashboard or rendered report exists.
- Use OpenAI Developers only if adding OpenAI API-backed analysis or app features.
