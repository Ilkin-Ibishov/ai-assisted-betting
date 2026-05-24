# Task 66 - Daily Decision Dashboard Simplification

Status: completed

## Goal

Refocus the dashboard from an internal analytical cockpit into a daily paper-betting decision surface: recommendations first, source freshness second, diagnostics available only when needed.

## What Changed

- Renamed the primary dashboard framing to "Daily Betting Card" and "What should I consider today?"
- Reordered the React dashboard so the first visible panel is the daily betting card with:
  - best single summary
  - ranked paper combination count
  - AI approval position
  - AI review, next check, risk flags, odds movement, and filterable recommendations
- Renamed live process and guardrail panels to user-facing research concepts:
  - "Data freshness"
  - "Research guardrails"
- Kept the AI analyst panel visible in the main flow.
- Moved historical comparison report catalog, model metrics, charts, cross-report analysis, and run details into a collapsed "Historical diagnostics" section.
- Updated dashboard smoke expectations for the new first-screen hierarchy.
- Added implementation plan:
  - `docs/superpowers/plans/2026-05-24-daily-decision-dashboard.md`

## Verification

Completed checks:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
cd dashboard
npm run test
npm run lint
npm run build
$env:PLAYWRIGHT_CHANNEL='chrome'; npm run smoke
```

Result:

```text
Backend tests: 165 passed
Ruff: all checks passed
Dashboard tests: 29 passed
Dashboard lint: passed
Dashboard build: passed
Dashboard smoke: passed
```

## What's Next

- Replace the Railway worker's deterministic fixture snapshot with a safe fresh public/user-provided Misli snapshot workflow.
- Extend the scheduled worker so every daily collection can generate fresh recommendations, combinations, and AI review records.
- Add richer external football research inputs for league/team/player context before treating recommendations as product-complete.

## Blockers

- No dashboard simplification blocker remains.
- Real daily Misli coverage remains blocked by the safe fresh snapshot/source workflow.

## Technical Debt

No new code debt was introduced by the dashboard simplification. Existing product debt remains: current worker runs still depend on a deterministic fixture and recommendations do not yet consume richer club/player/stat sources.
