# Task 65 - Railway Scheduled Worker Service

Status: in progress

## Goal

Deploy a dedicated Railway worker service that runs `run-scheduled-paper-worker` on a cron schedule and shares the same Railway Postgres database as the API.

## What Changed

- Added `Dockerfile.worker`, a worker-specific runtime image that installs the Python package, copies fixture snapshots, initializes the database, and runs the one-shot scheduled paper worker.
- Made the worker command configurable through environment variables:
  - `WORKER_PROVIDER`
  - `WORKER_SNAPSHOT`
  - `WORKER_MODEL`
  - `WORKER_LEAGUE`
  - `WORKER_SEASON`
- Kept `LIVE_COLLECTION_ENABLED=true` as a required worker-service variable only.

## Verification

Run before completion:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
cd dashboard
npm run test
npm run lint
npm run build
$env:PLAYWRIGHT_CHANNEL='chrome'; npm run smoke
```

After deployment:

```powershell
python -m app.cli production-smoke --api-base-url https://ai-assisted-betting-production.up.railway.app --dashboard-url https://dashboard-production-0a69.up.railway.app
curl https://ai-assisted-betting-production.up.railway.app/api/live/worker-status
```

## What's Next

- Create or configure the Railway `worker` service.
- Set `DATABASE_URL=${{Postgres.DATABASE_URL}}` and `LIVE_COLLECTION_ENABLED=true`.
- Deploy with `Dockerfile.worker`.
- Configure Railway cron.
- Confirm a cron-managed worker run updates `/api/live/worker-status`.

## Blockers

- The first scheduled worker proof uses the deterministic fixture snapshot. Real repeated Misli collection still needs a safe public snapshot generation workflow before it replaces the fixture.

## Technical Debt

No code debt is intended. Operational debt remains until the worker consumes fresh public/user-provided snapshots instead of the deterministic fixture.
