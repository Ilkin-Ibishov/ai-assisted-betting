# Task 36 - Dashboard Selected-Run Insights

## Goal

Turn selected-run cross-report metrics into a compact interpretation so the dashboard explains whether the current model/bookmaker pair looks strong, noisy, or weak.

## Requirements

- Classify selected-run cross-report history as strong, noisy, or weak.
- Treat low settled sample histories as noisy.
- Consider ROI and latest calibration for stronger histories.
- Render the insight inside the cross-report panel.
- Add unit and smoke coverage for the insight behavior.

## Implementation

Status: completed

Added `buildSelectedRunInsight` in:

```text
dashboard/src/lib/metrics.ts
```

The insight panel renders above the cross-report trend controls and currently emits one of:

```text
Strong signal
Noisy sample
Weak signal
```

The helper uses average settled bets as a sample-size guard. When history is large enough, it checks whether ROI is positive and latest Brier/log-loss are at or better than the selected run's cross-report average.

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
report-registry timestamps instead of filesystem modified time
dashboard report metadata refinement
replay-analysis improvements
data-provider robustness
```

## Blockers

None.

## Technical Debt

No new documented technical debt.
