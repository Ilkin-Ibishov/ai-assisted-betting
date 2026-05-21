# Task 23 - Dashboard Scaffold

## Goal

Create the local analytical dashboard frontend workspace.

## Stack

```text
React
TypeScript
Vite
Tailwind CSS
shadcn/ui
TanStack Query
TanStack Table
Recharts
```

## Requirements

- Add a `dashboard/` frontend workspace.
- Configure TypeScript, Vite, Tailwind, and shadcn/ui.
- Add basic app shell layout for the analytical dashboard.
- Add API client wiring for the Dashboard Data API.

## Acceptance

The dashboard dev server starts locally and renders an app shell ready for comparison analytics.

## Implementation

Status: completed

Created `dashboard/` as a React + TypeScript + Vite frontend workspace with Tailwind CSS, shadcn-style local UI primitives, TanStack Query, TanStack Table, Recharts, and lucide-react.

The scaffold now includes:

```text
FastAPI proxy from /api to http://127.0.0.1:8000
React Query provider
comparison report API client
report selector
dashboard shell/sidebar
KPI preview cards
ROI chart preview
analysis guidance panel
TanStack Table run preview
```

Run commands:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.api:api --reload
cd dashboard
npm run dev -- --host 127.0.0.1 --port 5173
```

Verification:

```powershell
npm run lint
npm run build
```

Both frontend checks passed. `npm run build` emits a Vite chunk-size warning because Recharts is already included in the scaffold.

## Next

Proceed to Task 24 - Analytical Dashboard V1:

```text
sortable ranking table
metadata summary
sample-size warning panel
Brier/log-loss/settled-bet charts
run detail and model configuration surface
```

## Notes

Do not build a marketing landing page. The first screen should be the working dashboard shell.
