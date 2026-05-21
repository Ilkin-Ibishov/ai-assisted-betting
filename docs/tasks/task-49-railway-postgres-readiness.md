# Task 49 - Railway And Postgres Readiness

## Goal

Prepare the app for Railway staging deployment with production-like configuration and Postgres compatibility.

## Requirements

- Add production configuration documentation.
- Add or verify health/readiness endpoints.
- Verify SQLAlchemy models and migrations against Postgres.
- Define Railway service layout for API, dashboard, database, and worker.
- Document environment variables.
- Keep local SQLite support.

## Acceptance Criteria

- Implemented: a clean environment can run migrations and start the API through `python -m app.cli init-db`.
- Implemented: `/api/health` returns service and database status for Railway health checks.
- Implemented: dashboard can target deployed API URLs through `VITE_API_BASE_URL`.
- Implemented: Postgres compatibility is documented and migration bookkeeping is dialect-aware.
- Implemented: Railway start/build commands are documented.

## Implementation Notes

Task 49 added:

```text
/api/health
psycopg[binary] dependency
Postgres-safe schema_migrations table DDL
non-SQLite no-op migration recording for model-managed fresh databases
VITE_API_BASE_URL dashboard API base support
.env.example
docs/deployment/railway-readiness.md
```

SQLite legacy migrations remain SQLite-only. Fresh Postgres databases use SQLAlchemy model creation, then record the existing migration names as applied no-ops.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
cd dashboard
npm run test
npm run lint
npm run build
```

## Next

Task 50 - Scheduled Paper Worker.

## Blockers

None. Task 46 run scoping, Task 47 relative Misli dates, and Task 52 provider-health analysis are complete.

## Technical Debt

No new unresolved debt. SQLite legacy migrations remain intentionally SQLite-only; Postgres uses model-managed fresh schema creation for staging.
