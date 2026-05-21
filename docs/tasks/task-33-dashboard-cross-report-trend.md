# Task 33 - Dashboard Cross-Report Trend

## Goal

Make the selected model/bookmaker cross-report history easier to scan with a visual ROI trend.

## Requirements

- Add testable helper logic for chart-ready cross-report trend rows.
- Render the selected run's ROI trend chronologically.
- Keep Recharts code lazy-loaded so dashboard bundle size remains controlled.
- Preserve existing cross-report table and selection behavior.
- Add smoke coverage for the rendered trend chart.

## Implementation

Status: completed

Added `buildCrossReportTrendRows` in:

```text
dashboard/src/lib/metrics.ts
```

Added a lazy-loaded Recharts component:

```text
dashboard/src/components/dashboard/cross-report-trend-chart.tsx
```

The chart renders inside the cross-report comparison panel and shows ROI percentage movement from oldest to newest recent report.

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
dashboard chart polish for calibration trends
report-registry timestamps instead of filesystem modified time
replay-analysis improvements
data-provider robustness
```

## Blockers

None.

## Technical Debt

No new documented technical debt.
