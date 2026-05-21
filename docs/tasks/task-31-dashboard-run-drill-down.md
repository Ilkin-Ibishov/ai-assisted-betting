# Task 31 - Dashboard Run Drill-Down

## Goal

Make the selected run detail panel more analytical by showing how the active model/bookmaker run compares with the report average.

## Requirements

- Add selected-run comparison math in a testable frontend helper.
- Show deltas for ROI, Brier score, log loss, and settled bets.
- Preserve the existing run ranking table and row-selection behavior.
- Add smoke coverage for the rendered drill-down after selecting a row.

## Implementation

Status: completed

Added `buildRunComparison` in:

```text
dashboard/src/lib/metrics.ts
```

The helper computes report averages and selected-run deltas, rounded to four decimal places before display formatting.

The run detail panel now includes:

```text
Against report average
ROI delta
Brier delta
Log loss delta
Settled delta
```

Smoke coverage now checks the drill-down values after selecting `elo / Avg`.

## Verification

Passed before docs-only updates:

```powershell
cd dashboard
npm run test
npm run lint
npm run build
```

Full verification is still required after this task's docs are saved:

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

Potential next phases:

```text
dashboard cross-report comparison view
report-registry timestamps instead of filesystem modified time
replay-analysis improvements
data-provider robustness
```

## Blockers

None.

## Technical Debt

No new documented technical debt.
