# Task 24 - Analytical Dashboard V1

## Goal

Build the first usable dashboard for comparison tracking and model-result analysis.

## Requirements

Build views/components for:

```text
comparison selector
metadata summary
sample-size warning panel
winners/KPI panels
sortable model-bookmaker ranking table
ROI chart
Brier score chart
log loss chart
settled sample-size chart
analysis / next experiment panel
```

## Acceptance

A user can open the local dashboard, select a comparison report, and inspect rankings, charts, sample-size warnings, and next experiment guidance.

## Implementation

Status: completed

Implemented the first usable analytical dashboard on top of the Task 23 scaffold.

Added dashboard features:

```text
metadata summary
sample-size warning panel
best ROI / best Brier / best log-loss KPI cards
total settled bets KPI
analysis status KPI
ROI chart
Brier score chart
log-loss chart
settled-bets chart
sortable model/bookmaker ranking table
selected-run detail panel
model configuration display
```

Added frontend analytical helpers:

```text
rankRuns
getMetricLeader
buildChartRows
summarizeMetadata
```

Added frontend test harness:

```powershell
cd dashboard
npm run test
```

Cleaned up unused Vite starter CSS and image assets after the dashboard replaced the starter screen.

TDD note:

The `src/lib/metrics.test.ts` suite was written first and failed because `src/lib/metrics.ts` did not exist. The helper implementation was then added and the tests passed.

## Verification

Passed:

```powershell
cd dashboard
npm run test
npm run lint
npm run build
```

Browser screenshots were checked with Playwright fallback using Microsoft Edge because the Browser plugin tools were not callable in this session:

```text
desktop 1440x1100 full-page
mobile 390x1000 full-page
```

The build still emits the existing Vite chunk-size warning documented in the technical debt register.

## Next

Proceed to Task 25 - Dashboard QA:

```text
component-level frontend tests
dashboard/API value contract checks
repeatable browser smoke checks
desktop/mobile overlap checks
source-report-to-rendered-value verification
```

## Notes

The UI should be dense, calm, and analytical. Avoid landing-page styling and decorative hero sections.
