# Daily Paper Trading Journal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic daily paper-only journal that turns recommendations, AI review, quality counts, open bets, and settled outcomes into one traceable learning record.

**Architecture:** Add a first-class `paper_journal_entries` table and a `DailyPaperJournalService` that composes existing database facts without inventing analysis. Expose the latest/generated journal through CLI and API, then show the latest journal summary in the dashboard daily card area.

**Tech Stack:** Python, SQLAlchemy ORM, Typer, FastAPI, pytest, React, TanStack Query, Vitest.

---

### Task 1: Journal Persistence And Service

**Files:**
- Modify: `app/db/models.py`
- Modify: `app/db/migrations.py`
- Create: `app/services/daily_paper_journal_service.py`
- Test: `tests/unit/test_daily_paper_journal_service.py`
- Test: `tests/unit/test_database.py`

- [ ] **Step 1: Write failing service tests**

Create tests for no-candidate, candidate-ready, AI-rejected, and settled-result states. Each test should call `DailyPaperJournalService(engine).generate(journal_date="2026-06-04")` and assert `decision_state`, `summary`, `source_ids`, `quality_snapshot`, and `settled_since_previous_journal`.

- [ ] **Step 2: Write failing migration test**

Add a test that `init_db()` creates/upgrades `paper_journal_entries` and records `011_create_paper_journal_entries`.

- [ ] **Step 3: Run tests to verify failure**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_daily_paper_journal_service.py tests/unit/test_database.py::test_init_db_creates_paper_journal_entries -q`
Expected: FAIL because the service/table do not exist.

- [ ] **Step 4: Implement minimal persistence and deterministic journal generation**

Add `PaperJournalEntry` with unique `journal_date`, `decision_state`, `summary_json`, `source_ids_json`, `created_at`, and `updated_at`. Implement upsert-style generation, latest lookup, and deterministic states: `no_candidates`, `candidate_ready`, `ai_rejected`, `settled_learning`.

- [ ] **Step 5: Run tests to verify pass**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_daily_paper_journal_service.py tests/unit/test_database.py -q`
Expected: PASS.

### Task 2: CLI And API

**Files:**
- Modify: `app/cli.py`
- Modify: `app/api.py`
- Test: `tests/integration/test_cli.py`
- Test: `tests/unit/test_dashboard_api.py`

- [ ] **Step 1: Write failing CLI/API tests**

Add tests for `daily-paper-journal` CLI output and `GET /api/live/daily-journal/latest`. The API test should return 404 when missing and return the latest persisted journal when present.

- [ ] **Step 2: Run tests to verify failure**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_dashboard_api.py::test_live_daily_journal_latest_endpoint_returns_latest tests/integration/test_cli.py::test_daily_paper_journal_command_persists_entry -q`
Expected: FAIL because command/endpoint do not exist.

- [ ] **Step 3: Implement CLI/API**

Add `daily-paper-journal` command that generates and prints date, decision state, and key counts. Add latest endpoint and payload helper.

- [ ] **Step 4: Run tests to verify pass**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_dashboard_api.py tests/integration/test_cli.py -q`
Expected: PASS.

### Task 3: Dashboard Journal Summary

**Files:**
- Modify: `dashboard/src/lib/api.ts`
- Modify: `dashboard/src/lib/api.test.ts`
- Modify: `dashboard/src/App.tsx`

- [ ] **Step 1: Write failing API client test**

Add `fetchLatestDailyJournal()` test asserting the client calls `/api/live/daily-journal/latest` and maps the journal type.

- [ ] **Step 2: Run test to verify failure**

Run: `cd dashboard; npm run test -- --run src/lib/api.test.ts`
Expected: FAIL because the client function does not exist.

- [ ] **Step 3: Implement dashboard fetch and panel**

Add `DailyPaperJournal` type/fetcher and render a compact latest journal card in the daily decision surface, near recommendation quality and AI review.

- [ ] **Step 4: Run dashboard verification**

Run: `cd dashboard; npm run test -- --run; npm run lint; npm run build`
Expected: PASS.

### Task 4: Docs And Final Verification

**Files:**
- Modify: `docs/tasks/task-75-daily-paper-trading-journal.md`
- Modify: `docs/agent/02_IMPLEMENTATION_ORDER.md`
- Modify: `docs/agent/05_TECHNICAL_DEBT.md`

- [ ] **Step 1: Mark Task 75 complete**

Record implemented journal behavior, verification, and remaining future work.

- [ ] **Step 2: Run final verification**

Run:
`.\.venv\Scripts\python.exe -m pytest tests/unit/test_daily_paper_journal_service.py tests/unit/test_dashboard_api.py tests/integration/test_cli.py -q`
`.\.venv\Scripts\python.exe -m ruff check app tests`
`cd dashboard; npm run test -- --run; npm run lint; npm run build`

- [ ] **Step 3: Commit**

Run:
`git add app dashboard docs tests`
`git commit -m "Add daily paper trading journal"`
