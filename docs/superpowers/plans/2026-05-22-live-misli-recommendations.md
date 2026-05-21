# Live Misli Recommendations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deployed paper-only live Misli.az intelligence loop that collects public football odds, generates disciplined recommendations and combinations, reviews them with AI, and displays them in the dashboard.

**Architecture:** The deterministic pipeline remains the decision source: scraper/provider -> live cycle -> odds movement -> recommendation engine -> combination engine -> AI review -> dashboard. AI reviews structured evidence and risk; it must not place bets, automate bookmaker accounts, or claim certainty.

**Tech Stack:** Python, SQLAlchemy, FastAPI, pytest, Ruff, Playwright snapshot tooling, React, Vite, shadcn-style UI, Vitest, Railway, Postgres.

---

## File Structure

- `tools/misli-public-snapshot.mjs`: browser-facing public snapshot extraction.
- `app/providers/misli_public.py`: parse and normalize Misli public snapshots.
- `app/services/live_collection_service.py`: collect and persist provider data.
- `app/services/live_cycle_service.py`: orchestrate paper live cycles.
- `app/services/recommendation_service.py`: new deterministic single recommendation scoring.
- `app/services/combination_service.py`: new deterministic paper combination scoring.
- `app/services/ai_analysis_service.py`: add recommendation and combination review modes.
- `app/db/models.py`: add odds movement, recommendation, and combination tables when needed.
- `app/db/repositories.py`: persistence helpers for new live intelligence records.
- `app/api.py`: expose recommendation, combination, and operational status endpoints.
- `dashboard/src/lib/*.ts`: add recommendation API helpers and formatters.
- `dashboard/src/App.tsx`: add recommendation and operational guardrail views.
- `docs/tasks/task-53-*.md` through `docs/tasks/task-62-*.md`: task-by-task scope.

## Task Sequence

### Task 50: Scheduled Paper Worker

**Files:**
- Modify: `app/cli.py`
- Modify: `app/services/live_cycle_service.py`
- Modify: `docs/tasks/task-50-scheduled-paper-worker.md`

- [ ] Write tests for single-run worker execution, duplicate protection, and failed-provider isolation.
- [ ] Add a CLI command that runs one scheduled paper cycle and exits.
- [ ] Add configurable cadence/env docs without starting a long-running local daemon by default.
- [ ] Run full backend and dashboard verification.
- [ ] Commit and push.

### Task 53: Misli Live Scraper Hardening

**Files:**
- Modify: `tools/misli-public-snapshot.mjs`
- Modify: `app/providers/misli_public.py`
- Test: `tests/unit/test_live_provider_contract.py`
- Test: `tests/unit/test_football_data_provider.py` or a new `tests/unit/test_misli_public_provider.py`

- [ ] Add parser tests for valid rows, malformed rows, relative dates, absolute dates, and odds formats.
- [ ] Harden extraction to include event identity, league, teams, kickoff, market, outcome, odds, and source metadata.
- [ ] Fail closed when required fields are missing.
- [ ] Update provider-health analysis inputs.
- [ ] Run full verification, update docs, commit and push.

### Task 54: Live Odds Movement Tracking

**Files:**
- Modify: `app/db/models.py`
- Modify: `app/db/repositories.py`
- Modify: `app/db/migrations.py`
- Modify: `app/services/live_collection_service.py`
- Modify: `app/api.py`
- Test: `tests/unit/test_database.py`
- Test: `tests/unit/test_dashboard_api.py`

- [ ] Add odds snapshot persistence tests before implementation.
- [ ] Add schema/model support for odds movement history.
- [ ] Store repeated snapshots without duplicating event identity.
- [ ] Expose movement summaries through API.
- [ ] Run full verification, update docs, commit and push.

### Task 55: Paper Bet Recommendation Engine

**Files:**
- Create: `app/services/recommendation_service.py`
- Modify: `app/db/models.py`
- Modify: `app/db/repositories.py`
- Modify: `app/cli.py`
- Modify: `app/api.py`
- Test: `tests/unit/test_recommendation_service.py`

- [ ] Write tests for positive edge, negative edge, stale odds, unhealthy provider, and low confidence.
- [ ] Implement deterministic scoring with explicit reject reasons.
- [ ] Persist recommendation records linked to live run and snapshot inputs.
- [ ] Add CLI/API access.
- [ ] Run full verification, update docs, commit and push.

### Task 56: Paper Bet Combination Engine

**Files:**
- Create: `app/services/combination_service.py`
- Modify: `app/db/models.py`
- Modify: `app/db/repositories.py`
- Modify: `app/api.py`
- Test: `tests/unit/test_combination_service.py`

- [ ] Write tests for duplicate-event rejection, correlation rejection, stale-leg rejection, max-leg enforcement, and ranking.
- [ ] Implement disciplined combination generation from accepted recommendation legs.
- [ ] Persist combinations and expose them through API.
- [ ] Run full verification, update docs, commit and push.

### Task 57: AI Recommendation Review Layer

**Files:**
- Modify: `app/services/ai_analysis_service.py`
- Modify: `app/services/ai_prompt_registry.py`
- Modify: `app/services/ai_analysis_evals.py`
- Modify: `app/cli.py`
- Modify: `app/api.py`
- Test: `tests/unit/test_ai_analysis_service.py`
- Test: `tests/unit/test_ai_analysis_evals.py`

- [ ] Add eval fixtures for recommendation and combination review.
- [ ] Add deterministic fallback review mode.
- [ ] Add optional LLM-backed provider only through official OpenAI docs and secure key handling.
- [ ] Persist review state and expose it through API.
- [ ] Run full verification, update docs, commit and push.

### Task 58: Recommendation Dashboard

**Files:**
- Modify: `dashboard/src/App.tsx`
- Create: `dashboard/src/lib/recommendations.ts`
- Create: `dashboard/src/lib/recommendations.test.ts`
- Modify: `dashboard/scripts/dashboard-smoke.mjs`
- Modify: `docs/specs/dashboard.md`

- [ ] Add formatter tests for recommendation grades, risk flags, odds movement, and AI states.
- [ ] Add ranked singles and combinations view.
- [ ] Add filters for grade, confidence, league, market, provider health, and AI approval.
- [ ] Extend smoke tests for desktop and mobile readability.
- [ ] Run full verification, update docs, commit and push.

### Task 59: Historical Recommendation Backtesting

**Files:**
- Create: `app/services/recommendation_backtest_service.py`
- Modify: `app/cli.py`
- Modify: `app/services/analysis_service.py`
- Test: `tests/unit/test_recommendation_backtest_service.py`
- Test: `tests/integration/test_cli.py`

- [ ] Write tests for deterministic report generation and threshold-sensitive ranking changes.
- [ ] Replay recommendation rules on historical and stored paper-cycle data.
- [ ] Export reports consumable by the dashboard catalog.
- [ ] Add AI analysis over backtest results.
- [ ] Run full verification, update docs, commit and push.

### Task 60: Railway Worker Deployment And Monitoring

**Files:**
- Modify: `docs/deployment/railway-readiness.md`
- Modify: `.env.example`
- Modify: `app/api.py`
- Modify: `dashboard/scripts/dashboard-smoke.mjs`

- [ ] Add deployment smoke checks for API, DB, dashboard, worker freshness, and recommendation endpoint.
- [ ] Document Railway service topology and env vars.
- [ ] Add operational endpoint if needed.
- [ ] Run full local verification and deployed smoke where credentials/environment are available.
- [ ] Commit and push.

### Task 61: Operational Guardrails And Alerting

**Files:**
- Create: `app/services/operational_guardrail_service.py`
- Modify: `app/api.py`
- Modify: `dashboard/src/App.tsx`
- Test: `tests/unit/test_operational_guardrail_service.py`

- [ ] Write tests for stale provider data, repeated worker failures, unsafe AI output, and empty recommendations.
- [ ] Implement warning/critical guardrail states.
- [ ] Surface guardrails in API and dashboard.
- [ ] Document remediation hints.
- [ ] Run full verification, update docs, commit and push.

### Task 62: Final Production Readiness Review

**Files:**
- Create: `docs/deployment/final-readiness-review.md`
- Modify: `docs/agent/05_TECHNICAL_DEBT.md`
- Modify: `docs/agent/04_OPEN_QUESTIONS.md`

- [ ] Run full local verification.
- [ ] Run deployed smoke verification if Railway is configured.
- [ ] Audit safety, scraping, AI, recommendation quality, deployment, and monitoring.
- [ ] Write pass/fail readiness report.
- [ ] Commit and push.

## Self-Review

- Spec coverage: Tasks cover automatic scheduling, Misli hardening, odds history, recommendations, combinations, AI review, dashboard, backtesting, deployment, monitoring, and readiness audit.
- Placeholder scan: No task uses TBD/TODO/fill-in placeholders.
- Type consistency: New service names are consistent across task docs and this plan.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-22-live-misli-recommendations.md`.

Recommended execution: implement Task 50 first, then Tasks 53 through 62 in order. Task 51 remains the deployment runbook task and should be updated alongside Task 60 when deployment becomes concrete.
