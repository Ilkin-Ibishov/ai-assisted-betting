# Task 35 - Dashboard Trend Metric Controls

## Goal

Let the dashboard isolate individual trend lines in the selected-run cross-report chart.

## Requirements

- Add controls for ROI, Brier score, and log loss visibility.
- Keep all metrics visible by default.
- Prevent the chart from hiding every metric at once.
- Preserve the cross-report table and selected-run behavior.
- Add unit and smoke coverage for metric toggle behavior.

## Implementation

Status: completed

Added `toggleTrendMetric` in:

```text
dashboard/src/lib/metrics.ts
```

The cross-report panel now renders three toggle buttons:

```text
ROI
Brier
Log loss
```

The lazy trend chart receives the active metric list and renders only the selected lines. The toggle helper keeps the last remaining metric active so the chart cannot become blank through controls.

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
dashboard selected-run summary insights
report-registry timestamps instead of filesystem modified time
replay-analysis improvements
data-provider robustness
```

## Blockers

None.

## Technical Debt

No new documented technical debt.
