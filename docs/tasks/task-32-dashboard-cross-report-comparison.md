# Task 32 - Dashboard Cross-Report Comparison

## Goal

Let the dashboard compare the selected model/bookmaker pair across recent comparison reports.

## Requirements

- Add testable helper logic for extracting the selected model/bookmaker from multiple reports.
- Keep rows sorted newest first.
- Render a compact cross-report table in the dashboard.
- Preserve existing catalog, chart, drill-down, and row-selection behavior.
- Add smoke coverage for the rendered cross-report panel.
- Keep detail reads usable for older comparison reports where structured analysis cannot be derived.

## Implementation

Status: completed

Added `buildCrossReportRows` in:

```text
dashboard/src/lib/metrics.ts
```

The dashboard now fetches details for recent catalog reports with React Query and renders a cross-report comparison table for the active selected run.

The comparison detail endpoint now returns the report plus `analysis_error` when structured analysis cannot be derived from an older report. The dedicated analysis endpoint remains strict and still returns an error for invalid analysis payloads.

The panel includes:

```text
report name
modified date
ROI
Brier score
log loss
settled bets
```

Smoke coverage checks that the panel renders after selecting `elo / Avg` and that at least one expected recent-report ROI appears.

## Verification

Passed:

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
cross-report trend chart for selected run metrics
report-registry timestamps instead of filesystem modified time
replay-analysis improvements
data-provider robustness
```

## Blockers

None.

## Technical Debt

No new documented technical debt.
