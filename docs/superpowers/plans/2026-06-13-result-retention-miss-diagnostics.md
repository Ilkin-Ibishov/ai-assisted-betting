# Result Retention Miss Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Misli result retention misses visible without settling paper bets from weak evidence.

**Architecture:** Extend the existing Misli result job service with a retention-miss classifier that marks repeatedly missed open paper-bet result jobs as `unresolvable` with a precise reason. Keep settlement unchanged; unresolved paper bets remain open until a proven result source is added.

**Tech Stack:** Python, SQLAlchemy, pytest, Ruff, Railway.

---

### Task 1: Add Retention-Miss Classification

**Files:**
- Modify: `app/services/misli_result_service.py`
- Test: `tests/unit/test_misli_result_service.py`

- [ ] **Step 1: Write failing tests**

Add tests that seed an open paper bet with repeated `result not found in Misli response` attempts after kickoff, run collection with an empty Misli payload, and assert the result job becomes `unresolvable` with a `provider_retention_miss` diagnostic. Also assert a retention-miss job is not reopened by `_ensure_result_jobs`.

- [ ] **Step 2: Implement minimal classifier**

Add constants for retention miss reason and window. In `_retire_unresolvable_result_jobs`, if a stale not-found job belongs to an open paper bet, mark `status="unresolvable"` and `last_error` to the retention-miss message. In `_ensure_result_jobs`, do not reopen an unresolvable open-bet job whose `last_error` is the retention-miss message.

- [ ] **Step 3: Expose diagnostic reason**

Update `_job_payload` to include `diagnostic_reason`, returning `provider_retention_miss` for the new message and preserving existing `unresolvable` behavior.

- [ ] **Step 4: Verify**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_misli_result_service.py
.\.venv\Scripts\python.exe -m ruff check app\services\misli_result_service.py tests\unit\test_misli_result_service.py
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

Expected: all tests pass and Ruff reports no issues.

### Task 2: Document And Deploy Proof

**Files:**
- Modify: `docs/tasks/task-93-fallback-result-source-retention.md`

- [ ] **Step 1: Update task notes**

Record that the first Task 93 slice classifies provider retention misses but does not yet add fallback settlement.

- [ ] **Step 2: Commit and push**

```powershell
git add app/services/misli_result_service.py tests/unit/test_misli_result_service.py docs/tasks/task-93-fallback-result-source-retention.md docs/superpowers/plans/2026-06-13-result-retention-miss-diagnostics.md
git commit -m "Classify Misli result retention misses"
git push origin HEAD:main
```

- [ ] **Step 3: Verify Railway**

Wait until API and worker deploy the pushed commit, then run production smoke and inspect `/api/live/result-jobs` for the remaining open paper-bet jobs.
