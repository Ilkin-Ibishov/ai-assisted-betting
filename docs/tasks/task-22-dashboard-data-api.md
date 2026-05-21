# Task 22 - Dashboard Data API

## Goal

Expose comparison reports and analysis output through a local read-only API for the future React dashboard.

## Stack

Use FastAPI for the API layer.

## Requirements

Add endpoints:

```text
GET /api/reports/comparisons
GET /api/reports/comparisons/{name}
GET /api/reports/comparisons/{name}/analysis
```

The API should read from:

```text
reports/*_comparison.json
```

and reuse the existing comparison analysis service for analysis output.

Report names in URLs should use the report stem without `_comparison.json`.

Example:

```text
reports/e0_compare_comparison.json -> /api/reports/comparisons/e0_compare
```

Run locally with:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.api:api --reload
```

## Acceptance

The API can list existing comparison reports, return one comparison JSON payload with structured analysis, and return analysis data for the same report.

## Implementation Notes

Implemented in `app/api.py` and `app/services/analysis_service.py`.

What was done:

- Added FastAPI, Uvicorn, and HTTPX dependencies.
- Added read-only comparison report list, detail, and analysis endpoints.
- Added structured analysis output for dashboard use.
- Added local CORS support for the Vite dashboard dev server.
- Added FastAPI `TestClient` coverage.

What's next:

- Scaffold the React/Vite/shadcn dashboard workspace.

Blockers:

- None.

Technical debt:

- No new technical debt introduced.

## Notes

This task should be implemented before scaffolding the React dashboard so the frontend has a stable data contract.
