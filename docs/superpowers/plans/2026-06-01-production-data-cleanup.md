# Production Data Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the live betting dashboard truthful by exposing unsafe open paper bets, enabling safe cleanup, and preparing settlement automation.

**Architecture:** Keep cleanup and ledger classification in backend services, expose concise summary fields through the existing API, and let the dashboard render explicit actionable/unsafe/awaiting-result states. Use Railway only after local tests and production smoke checks pass.

**Tech Stack:** Python, FastAPI, SQLAlchemy, Typer, React, Vite, Vitest, pytest, Railway.

---

### Task 1: Make Ledger Summary Truthful

**Files:**
- Modify: `app/services/bet_ledger_service.py`
- Modify: `tests/unit/test_bet_ledger_service.py`
- Modify: `dashboard/src/lib/api.ts`
- Modify: `dashboard/src/lib/bet-ledger.ts`
- Modify: `dashboard/src/lib/bet-ledger.test.ts`
- Modify: `dashboard/src/components/dashboard/bet-ledger-panel.tsx`

- [ ] Add backend summary fields for `valid_open_count`, `unsafe_open_count`, and `candidate_count`.
- [ ] Add a failing backend test with one valid future bet, one unsafe future bet, one past open bet, and one candidate.
- [ ] Implement the summary fields from date-filtered rows.
- [ ] Add dashboard type and helper tests for the new fields.
- [ ] Render summary cards that distinguish actionable fresh bets from unsafe open bets.
- [ ] Run `pytest tests/unit/test_bet_ledger_service.py -q`.
- [ ] Run `npm --prefix dashboard test -- --run src/lib/bet-ledger.test.ts`.

### Task 2: Cleanup Preview and Execution Safety

**Files:**
- Modify: `app/services/paper_bet_maintenance_service.py`
- Modify: `tests/unit/test_paper_bet_maintenance_service.py`
- Modify: `app/api.py`
- Modify: `tests/unit/test_dashboard_api.py`
- Modify: `app/cli.py`
- Modify: `tests/integration/test_cli.py`

- [ ] Ensure dry-run reports unsafe reason counts without mutating rows.
- [ ] Ensure execution writes decision-log entries and sets `status="void"` with zero P/L.
- [ ] Ensure the admin API returns the same preview/execution summary.
- [ ] Run targeted backend/API/CLI tests.

### Task 3: Settlement Automation Design Hook

**Files:**
- Modify: `app/services/scheduled_worker_service.py`
- Modify: `tests/unit/test_scheduled_paper_worker_service.py`
- Modify: `app/config.py`
- Modify: `docs/tasks/task-42-live-result-collection-settlement.md`

- [ ] Add a config flag for settlement automation, defaulting off.
- [ ] When enabled, run settlement after the worker cycle and include settlement counts in worker output.
- [ ] Keep result collection separate until a reliable result provider is configured.
- [ ] Test disabled and enabled behavior.

### Task 4: Operational Noise Cleanup

**Files:**
- Modify: snapshot producer script or Docker entrypoint after locating the log source.
- Modify: API static/favicon handling if needed.

- [ ] Change successful snapshot posts from error-level logs to info-level logs.
- [ ] Add or route a favicon so API logs are not polluted by `/favicon.ico` 404s.
- [ ] Verify Railway logs are cleaner after deploy.

### Task 5: Deploy and Verify

**Files:**
- No source edits unless verification reveals defects.

- [ ] Run full backend tests touched by the cleanup and ledger changes.
- [ ] Run dashboard tests and production build.
- [ ] Deploy API/dashboard/worker only for services affected by the completed tasks.
- [ ] Verify `/api/health`, `/api/live/status`, `/api/live/bet-ledger`, and dashboard rendering in browser.
- [ ] Report production data counts before and after cleanup.
