# Daily Decision Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current engineering-heavy dashboard landing view with a simple daily paper-betting decision surface for Misli.az research.

**Architecture:** Keep the existing React + Vite + shadcn-style dashboard and API contracts. Reorder the UI so paper recommendations, combinations, AI review, data freshness, and source health are the primary view; move historical comparison metrics into a diagnostics section.

**Tech Stack:** React, Vite, TypeScript, TanStack Query/Table, Tailwind CSS, lucide-react, Vitest, Playwright smoke checks.

---

### Task 1: Product-Focused App Shell

**Files:**
- Modify: `dashboard/src/App.tsx`
- Test: `dashboard/scripts/dashboard-smoke.mjs`

- [x] Rename the main surface from “Analytical Dashboard / Comparison workspace” to “Daily Betting Card”.
- [x] Replace sidebar navigation with decision-focused labels: Today’s card, Research inputs, Diagnostics.
- [x] Keep “paper-only” wording visible so the UI does not imply real-money execution.
- [x] Keep refresh and report select controls available but visually secondary.

### Task 2: Daily Decision Priority

**Files:**
- Modify: `dashboard/src/App.tsx`
- Test: `dashboard/src/lib/recommendations.test.ts`

- [x] Render the recommendation panel first.
- [x] Rename “Recommendation dashboard” to “Daily betting card”.
- [x] Show AI approval, top risk flags, AI review, next check, best singles, and ranked combinations in one first-view workflow.
- [x] Keep filters but make them secondary to the daily card.

### Task 3: Research Inputs and Data Freshness

**Files:**
- Modify: `dashboard/src/App.tsx`
- Test: `dashboard/scripts/dashboard-smoke.mjs`

- [x] Show live process and operational guardrails directly after the daily card.
- [x] Rename process language to “Data freshness” and “Research guardrails”.
- [x] Keep latest run, provider, open paper bets, errors, and guardrail remediation visible.

### Task 4: Diagnostics Section

**Files:**
- Modify: `dashboard/src/App.tsx`
- Test: `dashboard/scripts/dashboard-smoke.mjs`

- [x] Move report catalog, metadata, sample size, metric cards, charts, cross-report comparison, guidance, run detail, and run ranking under a collapsible diagnostics block.
- [x] Default diagnostics closed so the daily product surface is not cluttered.
- [x] Preserve existing test ids where possible so existing helper logic remains useful.

### Task 5: Documentation and Verification

**Files:**
- Modify: `docs/agent/00_READ_ME_FIRST.md`
- Modify: `docs/agent/02_IMPLEMENTATION_ORDER.md`
- Modify: `docs/agent/03_DOC_READING_MAP.md`
- Modify: `docs/agent/05_TECHNICAL_DEBT.md`
- Create: `docs/tasks/task-66-daily-decision-dashboard-simplification.md`

- [x] Record the dashboard product pivot and implementation status.
- [x] Record remaining technical debt: real fresh Misli/stat sources and daily recommendation generation pipeline.
- [x] Run full backend and dashboard verification before completion.
