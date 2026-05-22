# Analytical Dashboard

## Goal

Build a local analytical dashboard that helps track replay processes, comparison results, model performance, calibration quality, and next experiment guidance.

## Stack

```text
Frontend: React + TypeScript + Vite
UI: shadcn/ui + Tailwind CSS
Charts: Recharts
Tables: TanStack Table
Data fetching/state: TanStack Query
API layer: FastAPI
Data source: SQLite + reports/*.json
```

## Dashboard Principles

- Local-first.
- Read-only for the first dashboard version.
- Paper-betting only.
- Analytical and work-focused, not a marketing landing page.
- Dense but readable views for repeated comparison and experiment review.
- No bookmaker account automation or real-money betting actions.

## First Dashboard Views

### 1. Comparison Overview

Purpose:

- Select an existing comparison report.
- Show league, season, models, bookmakers, date filters, workers, and run count.
- Surface sample-size warning and next experiment guidance.

Core components:

```text
comparison selector
metadata summary
sample-size warning panel
analysis summary panel
```

### 2. Model And Bookmaker Rankings

Purpose:

- Compare ROI, Brier score, and log loss across model/bookmaker runs.
- Keep profitability and calibration visible side by side.

Core components:

```text
sortable ranking table
best ROI card
best Brier score card
best log loss card
```

### 3. Charts

Purpose:

- Make differences visible without replacing exact tables.

Initial charts:

```text
ROI by model/bookmaker
Brier score by model/bookmaker
Log loss by model/bookmaker
Settled bets by model/bookmaker
```

### 4. Run Detail

Purpose:

- Inspect one run's metrics and model configuration.

Core components:

```text
run KPI strip
model configuration block
profit/loss and sample-size metrics
```

## API Requirements

Add a FastAPI API layer that exposes report data to the dashboard.

Initial endpoints:

```text
GET /api/reports/comparisons
GET /api/reports/comparisons/{name}
GET /api/reports/comparisons/{name}/analysis
GET /api/live/status
GET /api/live/runs
GET /api/live/runs/{run_id}
GET /api/live/odds-movement
GET /api/live/recommendations
GET /api/live/combinations
GET /api/ai/recommendation-review/latest
```

Response data should come from existing comparison JSON and analysis service output. The first version does not need database write operations.

`{name}` is the comparison report stem without `_comparison.json`.

Example:

```text
reports/e0_compare_comparison.json -> e0_compare
```

Task 59 recommendation backtests also emit a companion report named:

```text
reports/<name>_comparison.json
```

with `metadata.report_type = recommendation_backtest`, comparison-style `runs`, and the canonical backtest payload under `recommendation_backtest`. This lets the existing dashboard catalog list historical recommendation backtests without a separate catalog endpoint.

The FastAPI app should be runnable with:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.api:api --reload
```

## Dashboard Data Contract

Comparison detail responses should expose:

```text
metadata
rankings
runs
analysis
```

Analysis should be structured for the frontend:

```text
text
sample_size.smallest
sample_size.largest
sample_size.warning
interpretation
next_experiment
```

Each run should include:

```text
model
bookmaker
total_bets
settled_bets
wins
losses
roi
profit_loss_units
average_odds
average_edge
brier_score
log_loss
roi_rank
brier_score_rank
log_loss_rank
model_config
```

## Live Process Data Contract

Task 43 added read-only live process endpoints for Task 44 dashboard monitoring.

`GET /api/live/status` returns:

```text
latest_run
latest_success
latest_failure
open_paper_bets
settled_paper_bets
runs_count
errors_count
```

`GET /api/live/runs` returns recent live runs newest-first. `GET /api/live/runs/{run_id}` returns one run or 404.

`GET /api/live/odds-movement` returns read-only current/opening/previous odds movement summaries grouped by match, bookmaker, market, and selection. Outcomes can be `active`, `missing`, or `stale`, with movement directions `new`, `up`, `down`, `stable`, `missing`, or `stale`.

`GET /api/live/recommendations` returns persisted deterministic paper recommendations newest-first. Records include grade, model probability, implied probability, edge, confidence, current odds, expected value, risk flags, and rationale.

`GET /api/live/combinations` returns ranked persisted paper-only combinations. Records include leg recommendation ids, leg count, model identity, grade, status, rank, combined odds, estimated probability, combined expected value, confidence score, risk flags, rationale, and creation time.

`GET /api/ai/recommendation-review/latest` returns the latest persisted AI-assisted advisory review for paper recommendations and combinations. The output includes approval state, concerns, confidence explanation, rejected assumptions, next checks, risk flags, and source record ids.

Task 58 added the dashboard recommendation surface. It displays:

```text
live paper recommendations
ranked paper combinations
odds movement direction
edge and confidence
risk flags
AI recommendation-review approval state
AI review next checks
filters for grade, market, confidence band, and AI approval state
```

The view remains read-only and does not expose bet placement or bookmaker account actions.

Task 59 added historical recommendation backtest exports. `backtest-recommendations` writes the canonical `_recommendation_backtest.json`, summary CSV, and dashboard-compatible `_comparison.json` companion report. `analyze-recommendation-backtest` persists an AI-assisted advisory summary for small samples, threshold sensitivity, ROI weakness, and combination underperformance.

Each live run payload includes:

```text
id
run_id
run_type
provider
league
season
status
started_at
finished_at
items_read
items_created
items_updated
items_skipped
errors_count
error_summary
model_name
created_at
```

Dashboard live process surfaces must remain read-only for the first monitor version.

## Implementation Phases

### Phase 22 - Dashboard Data API

Add FastAPI and read-only endpoints for comparison report listing, comparison details, and analysis text.

### Phase 23 - Dashboard Scaffold

Create `dashboard/` with React, TypeScript, Vite, Tailwind, shadcn/ui, TanStack Query, TanStack Table, and Recharts.

Implemented scaffold:

```text
dashboard Vite workspace
Tailwind CSS v4 Vite plugin
shadcn-style local UI primitives
React Query provider
relative /api client
Vite proxy to http://127.0.0.1:8000
comparison report selector
KPI, ROI chart, analysis, and run-table preview surfaces
```

Local development:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.api:api --reload
cd dashboard
npm run dev -- --host 127.0.0.1 --port 5173
```

### Phase 24 - Analytical Dashboard V1

Build the comparison overview, rankings table, KPI panels, and first charts.

Implemented V1 surfaces:

```text
comparison selector
metadata summary
sample-size warning panel
metric leader cards
ROI chart
Brier score chart
log-loss chart
settled-bets chart
sortable run ranking table
selected-run detail panel
model configuration block
analysis and next experiment panel
```

Frontend analytics helpers live in:

```text
dashboard/src/lib/metrics.ts
dashboard/src/lib/metrics.test.ts
```

### Phase 25 - Dashboard QA

Add frontend tests and browser verification for desktop and mobile viewports.

Implemented QA:

```text
Vitest analytics-helper tests
Playwright smoke script
API-to-rendered-value checks
desktop screenshot
mobile screenshot
table-row interaction check
console health gate
```

Command:

```powershell
cd dashboard
npm run smoke
```

The smoke script assumes the FastAPI API is running on `127.0.0.1:8000` and the Vite dashboard is running on `127.0.0.1:5173`.

### Phase 26 - Dashboard Bundle Optimization

Resolve the remaining dashboard bundle-size warning before adding more chart-heavy views.

Implemented:

```text
lazy-loaded Recharts metric chart module
main dashboard chunk below Vite warning threshold
chart chunk below Vite warning threshold
unchanged dashboard behavior verified by smoke test
```

### Phase 28 - Dashboard Report Catalog

Add a report catalog/history surface above the analytical panels.

Implemented:

```text
enriched comparison list API summary metrics
recent report catalog cards
catalog card report selection
catalog smoke assertions
```

Report summaries include:

```text
modified_at
total_settled_bets
best_roi
best_brier_score
best_log_loss
sample_size_smallest
sample_size_largest
```

### Phase 29 - Dashboard Report Catalog Filter

Hide pytest-generated reports from the default dashboard catalog.

Implemented:

```text
GET /api/reports/comparisons excludes pytest_* reports by default
GET /api/reports/comparisons?include_test_reports=true includes them
dashboard smoke fails if pytest_* reports appear in the default catalog
```

### Phase 30 - Dashboard Report Catalog Search

Add frontend search controls to narrow the local report catalog.

Implemented:

```text
catalog helper for sorting, filtering, and visible result limiting
search input in the report catalog panel
query matching across report name, filename, league, season, models, and bookmakers
empty state for no matching reports
unit tests for catalog visibility rules
smoke assertions for search, empty state, and restored selection behavior
```

### Phase 31 - Dashboard Run Drill-Down

Add selected-run comparison context inside the existing run detail panel.

Implemented:

```text
run comparison helper for report-average deltas
ROI, Brier, log loss, and settled-bet deltas for the selected run
unit tests for selected-run comparison math
smoke assertions for rendered drill-down values after row selection
```

### Phase 32 - Dashboard Cross-Report Comparison

Track the selected model/bookmaker run across recent reports.

Implemented:

```text
cross-report helper for extracting matching model/bookmaker rows
detail endpoint fallback that preserves legacy report reads when analysis is unavailable
recent-report detail queries for the active dashboard session
cross-report comparison table with ROI, Brier, log loss, and settled bets
unit tests for matching and newest-first ordering
unit tests for legacy report detail fallback
smoke assertions for rendered cross-report rows
```

### Phase 33 - Dashboard Cross-Report Trend

Visualize selected-run ROI movement across recent reports.

Implemented:

```text
cross-report trend helper with chronological chart rows
lazy-loaded Recharts line chart for selected-run ROI trend
trend chart inside the cross-report comparison panel
unit tests for trend row ordering and percentage conversion
smoke assertions for trend chart visibility
```

### Phase 34 - Dashboard Calibration Trend

Add calibration metrics to the selected-run cross-report trend chart.

Implemented:

```text
cross-report trend rows include Brier score and log loss
lazy-loaded trend chart renders ROI, Brier, and log-loss lines
panel label updated to ROI and calibration trend
unit tests for calibration trend row fields
smoke assertion for updated trend panel label
```

### Phase 35 - Dashboard Trend Metric Controls

Add metric visibility controls to the selected-run trend chart.

Implemented:

```text
trend metric toggle helper that keeps at least one metric visible
ROI, Brier, and log-loss toggle buttons in the cross-report panel
trend chart renders only selected metrics
unit tests for toggle behavior
smoke assertions for toggle active state changes
```

### Phase 36 - Dashboard Selected-Run Insights

Add a compact interpretation panel for the selected model/bookmaker pair.

Implemented:

```text
selected-run insight helper classifies cross-report history as strong, noisy, or weak
sample-size guard keeps small histories marked noisy
cross-report panel renders the insight above trend controls
unit tests for noisy, strong, and weak classifications
smoke assertions for rendered insight label
```

### Phase 37 - Dashboard Generated Timestamp Ordering

Prefer report-generated timestamps for dashboard catalog and trend ordering.

Implemented:

```text
comparison summary modified_at uses metadata.generated_at when valid
filesystem modified time remains the fallback for older reports
unit tests for generated_at preference
dashboard ordering benefits without frontend changes
```

### Phase 43 - Live Process Status API

Expose live paper process state to the dashboard without direct SQLite access.

Implemented:

```text
live status service
latest run/success/failure endpoint
recent run list endpoint
run detail endpoint
open and settled paper-bet counts
API tests for empty, successful, failed, listing, detail, and 404 states
```

### Phase 44 - Dashboard Process Monitor

Add an operational dashboard surface using the Task 43 API.

Implemented:

```text
latest live run status
provider/source label
latest run counters
error and skipped-record visibility
open and settled paper bet counts
last successful and failed run labels
empty-state handling
browser smoke coverage
```

## Non-Goals

- No live execution controls.
- No real-money betting actions.
- No auth or multi-user deployment in the first dashboard version.
- No dashboard writes back to SQLite in the first version.
