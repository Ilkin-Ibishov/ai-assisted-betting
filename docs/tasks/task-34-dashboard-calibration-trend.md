# Task 34 - Dashboard Calibration Trend

## Goal

Avoid judging selected-run movement by ROI alone by adding Brier score and log-loss trend lines to the cross-report chart.

## Requirements

- Extend cross-report trend rows with calibration metrics.
- Render ROI, Brier score, and log loss in the lazy-loaded trend chart.
- Preserve the existing cross-report table and selected-run behavior.
- Keep bundle size controlled through the existing lazy chart split.
- Add smoke coverage for the updated trend panel label.

## Implementation

Status: completed

Updated:

```text
dashboard/src/lib/metrics.ts
dashboard/src/components/dashboard/cross-report-trend-chart.tsx
dashboard/src/App.tsx
dashboard/scripts/dashboard-smoke.mjs
```

`buildCrossReportTrendRows` now includes:

```text
roi
brierScore
logLoss
```

The trend chart now renders three lines:

```text
ROI
Brier
Log loss
```

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
dashboard metric visibility controls
report-registry timestamps instead of filesystem modified time
replay-analysis improvements
data-provider robustness
```

## Blockers

None.

## Technical Debt

No new documented technical debt.
