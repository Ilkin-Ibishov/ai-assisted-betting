# Combination Risk Quarantine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Keep combinations visible for research while preventing them from driving primary paper-candidate readiness.

**Architecture:** Extend existing `CombinationService` risk flags and grading instead of replacing the engine. Carry quarantine state through API, AI review, backtest reports, and dashboard filtering using existing `risk_flags` payloads.

**Tech Stack:** Python, SQLAlchemy ORM, pytest, React, Vitest.

---

### Task 1: Combination Exposure Risk Flags

**Files:**
- Modify: `app/services/combination_service.py`
- Test: `tests/unit/test_combination_service.py`

- [x] **Step 1: Write failing tests for same-match, duplicate-team, same-league, high-leg, and independent-leg cases.**
- [x] **Step 2: Run `.\.venv\Scripts\python.exe -m pytest tests/unit/test_combination_service.py -q` and verify failure.**
- [x] **Step 3: Implement explicit quarantine risk flags and conservative grades.**
- [x] **Step 4: Rerun combination tests and verify pass.**

### Task 2: AI Review Separates Singles From Combinations

**Files:**
- Modify: `app/services/ai_analysis_service.py`
- Test: `tests/unit/test_ai_analysis_service.py`

- [x] **Step 1: Write failing AI review test proving combinations can be quarantined while singles remain actionable.**
- [x] **Step 2: Run the targeted AI test and verify failure.**
- [x] **Step 3: Add combination quarantine counts and risk flags without downgrading single candidate approval.**
- [x] **Step 4: Rerun AI analysis tests.**

### Task 3: Backtest And Dashboard Quarantine Visibility

**Files:**
- Modify: `app/services/recommendation_backtest_service.py`
- Modify: `dashboard/src/lib/api.ts`
- Modify: `dashboard/src/lib/recommendations.ts`
- Modify: `dashboard/src/App.tsx`
- Test: `tests/unit/test_recommendation_backtest_service.py`
- Test: `dashboard/src/lib/recommendations.test.ts`

- [x] **Step 1: Write failing tests for combination quarantine counts and dashboard exclusion from primary readiness.**
- [x] **Step 2: Implement report counts and dashboard experimental labeling/filtering.**
- [x] **Step 3: Run Python and dashboard tests.**

### Task 4: Docs And Final Verification

**Files:**
- Modify: `docs/tasks/task-76-combination-risk-quarantine.md`
- Modify: `docs/agent/02_IMPLEMENTATION_ORDER.md`
- Modify: `docs/agent/05_TECHNICAL_DEBT.md`

- [x] **Step 1: Mark Task 76 complete and record verification.**
- [x] **Step 2: Run final verification commands from the task.**
- [x] **Step 3: Commit with `git commit -m "Quarantine experimental combinations"`.**
