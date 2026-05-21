# Task 50 - Scheduled Paper Worker

## Goal

Add a safe recurring worker for paper-only live collection, prediction, settlement, and evaluation.

## Requirements

- Run only scoped paper-betting jobs.
- Never place real bets or automate bookmaker accounts.
- Use configurable cadence and provider enablement flags.
- Record every run in `live_runs`.
- Avoid overlapping executions.
- Surface stale data and failed runs to the dashboard.

## Acceptance Criteria

- Worker can run once locally and under Railway-style environment variables.
- Duplicate protection holds across repeated runs.
- Failed provider collection does not crash unrelated stages.
- Dashboard status reflects worker runs.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
cd dashboard
npm run test
npm run lint
npm run build
npm run smoke
```

## Next

Task 51 - Railway Deployment Runbook And Production Smoke.

## Blockers

Requires Task 46 and Task 49.

## Technical Debt

Record any scheduling workaround or Railway-specific limitation.
