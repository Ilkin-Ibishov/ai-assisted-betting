# ADR-0003 - Analytical Dashboard Stack

## Status

Accepted

## Context

Paper Odds Lab has a working offline/replay research core with comparison JSON, rankings, and analysis output. The next product direction is a local analytical dashboard for tracking replay processes and results.

The dashboard should stay aligned with the existing Python/SQLite CLI engine and should not introduce live betting, account automation, protected scraping, or unnecessary hosting complexity.

## Decision

Use this stack for the dashboard phase:

```text
Frontend: React + TypeScript + Vite
UI: shadcn/ui + Tailwind CSS
Charts: Recharts
Tables: TanStack Table
Data fetching/state: TanStack Query
API layer: FastAPI
Backend data source: existing SQLite database and reports/*.json artifacts
```

## Rationale

- React + Vite provides a fast local app without requiring server-side rendering.
- shadcn/ui fits an analytical/admin dashboard because components are local, editable, and Tailwind-native.
- Recharts is sufficient for first-pass ROI, Brier score, log loss, and sample-size visualizations.
- TanStack Table is appropriate for sortable/filterable model and bookmaker comparison tables.
- TanStack Query keeps API fetching explicit and testable.
- FastAPI fits the existing Python codebase and can expose SQLite/report data without introducing a separate backend language.

## Alternatives Considered

### Next.js

Rejected for now. It is powerful, but the project does not currently need SSR, public pages, auth, server components, or deployment-oriented routing.

### Streamlit

Rejected for the main dashboard. It would be faster for a prototype but gives less control over a polished analytical interface and long-term frontend architecture.

### Static HTML Reports

Rejected as the main direction. Static reports are useful, but the user wants a process/result tracking dashboard with richer interaction.

## Consequences

- A `dashboard/` frontend workspace will be added when implementation starts.
- A small FastAPI API layer should be added before or alongside the dashboard.
- Dashboard work should remain local-first and read from existing reports/database outputs.
- Frontend implementation should follow shadcn/ui conventions and avoid marketing-style landing pages.
