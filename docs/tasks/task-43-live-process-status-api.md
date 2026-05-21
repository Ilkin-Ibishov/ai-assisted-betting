# Task 43 - Live Process Status API

## Goal

Expose read-only API endpoints for live paper run and process status.

## Requirements

- Add FastAPI endpoints for latest live runs.
- Include latest success/failure status, counters, and error summaries.
- Include open paper bet counts and settlement status where practical.
- Keep endpoints read-only.

## Endpoint Direction

```text
GET /api/live/status
GET /api/live/runs
GET /api/live/runs/{run_id}
```

## Acceptance Criteria

- Implemented: API tests cover empty state, successful run, failed run, latest status, run listing, run detail, and missing-run 404.
- Implemented: dashboard can consume status without direct DB access through FastAPI.
- Implemented: no write operations are exposed.

## Implementation Notes

Task 43 added:

```text
app/services/live_status_service.py
GET /api/live/status
GET /api/live/runs
GET /api/live/runs/{run_id}
```

The status endpoint returns:

```text
latest_run
latest_success
latest_failure
open_paper_bets
settled_paper_bets
runs_count
errors_count
```

Run payloads include provider, run type, timestamps, counters, error summary, model name, league, and season. The API is read-only and uses the configured `DATABASE_URL`, with tests able to inject an isolated SQLite URL.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

## Next

Task 44 - Dashboard Process Monitor.

## Blockers

None for Task 43. Task 44 depends on these endpoints.

## Technical Debt

No new technical debt. Settlement status is represented by open versus settled paper-bet counts for MVP; deeper settlement breakdowns can be added during Task 44 if the UI needs them.
