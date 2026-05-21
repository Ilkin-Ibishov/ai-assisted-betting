# Task 25 - Dashboard QA

## Goal

Verify the analytical dashboard renders correctly and remains aligned with CLI/API outputs.

## Requirements

- Add frontend test coverage for key dashboard components.
- Add API contract checks where useful.
- Use browser verification for the local dashboard.
- Check desktop and mobile viewports.
- Confirm charts, tables, and warning panels render without overlap.

## Acceptance

Dashboard tests pass, browser smoke checks pass, and rendered dashboard values match the source comparison report.

## Implementation

Status: completed

Added repeatable dashboard QA:

```text
stable dashboard test IDs for key metric cards, selector, warning panel, ranking table, and selected-run label
Playwright smoke script at dashboard/scripts/dashboard-smoke.mjs
npm run smoke command
source API value checks against rendered dashboard metrics
desktop screenshot capture
mobile screenshot capture
run-row interaction check
console warning/error gate
```

The smoke script expects the local API and Vite dashboard to be running:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.api:api --host 127.0.0.1 --port 8000
cd dashboard
npm run dev -- --host 127.0.0.1 --port 5173
npm run smoke
```

It checks:

```text
reports indexed count
selected run count
best ROI
best Brier score
best log loss
total settled bets
sample-size range
analysis status
chart headings
run detail update after clicking a table row
desktop and mobile rendering
console health
```

## Fixes

The first smoke run caught Recharts console warnings about charts measuring at `-1` width and height during initial render. Replaced `ResponsiveContainer` with a measured chart container so charts render only after a real positive width is available.

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

`npm run build` still emits the known Vite bundle-size warning documented in the technical debt register.

## Next

Resolve the remaining dashboard bundle-size debt before adding more dashboard-heavy features.
