# Task 60 - Railway Worker Deployment And Monitoring

## Goal

Deploy the API, dashboard, database, and scheduled paper worker to Railway with operational monitoring.

## Requirements

- Separate Railway services for API, dashboard, Postgres, and scheduled worker where appropriate.
- Configure health checks for API, worker freshness, provider health, and database connectivity.
- Add deployment smoke commands and rollback notes.
- Ensure logs reveal scraper failures, stale data, AI review failures, and recommendation pipeline failures.
- Keep all deployment behavior paper-only.

## Acceptance Criteria

- Railway deployment can run scheduled paper cycles without local machine involvement.
- Dashboard shows fresh cycle status and recommendation state from deployed services.
- Deployment runbook includes exact environment variables, commands, smoke checks, and failure triage.
- Production smoke verifies API health, database health, dashboard load, worker freshness, and recommendation API response.

## Implementation Notes

Implemented in Task 60:

- Added `WorkerMonitoringService` over `live_runs.run_type = scheduled_paper_worker`.
- Added `GET /api/live/worker-status` with `healthy`, `status`, `freshness_minutes`, `fresh_after_minutes`, and latest worker run payload.
- Extended `production-smoke` to verify worker freshness through `/api/live/worker-status`.
- Extended `production-smoke` to verify the deployed recommendation endpoint through `/api/live/recommendations?limit=5`.
- Updated the Railway runbook with worker service topology, cron/cadence guidance, monitoring checks, smoke checks, and failure triage.
- Kept worker enablement paper-only through `LIVE_COLLECTION_ENABLED=true` on the worker service only.

## Verification

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

Task 61 - Operational Guardrails And Alerting.

## Blockers

No code blocker remains. Actual Railway scheduling still requires deployed service URLs, Railway project access, and a valid public/user-provided snapshot path or collection setup.

## Technical Debt

No new code debt. Railway cron cadence, cold starts, and service-to-service networking limits remain operational considerations documented in the runbook.
