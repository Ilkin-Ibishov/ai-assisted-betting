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

Requires Task 50 worker and Task 51 Railway runbook, with recommendation pipeline tasks completed for full monitoring.

## Technical Debt

Record Railway limitations around cron cadence, cold starts, and service-to-service networking.
