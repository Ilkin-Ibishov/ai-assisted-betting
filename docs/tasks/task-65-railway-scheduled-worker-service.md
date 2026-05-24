# Task 65 - Railway Scheduled Worker Service

Status: completed

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
- Created the Railway `worker` service.
- Set worker-only Railway variables, including shared `DATABASE_URL`, `LIVE_COLLECTION_ENABLED=true`, `MIN_EDGE=0.01`, and worker snapshot/model defaults.
- Deployed a worker-specific upload context using `Dockerfile.worker` as `Dockerfile`.
- Configured Railway cron through worker config-as-code with `deploy.cronSchedule="*/30 * * * *"`.
- Confirmed a cron-triggered worker run started at `2026-05-24T14:01:20Z` and refreshed `/api/live/worker-status`.

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

Completed deployment verification:

```text
worker service: worker
worker deployment: SUCCESS
cron schedule: */30 * * * *
cron-triggered run: completed at 2026-05-24T14:01:20Z
worker status: fresh
production-smoke with API and dashboard: passed
```

## What's Next

- Replace the deterministic fixture snapshot with a safe fresh public/user-provided snapshot generation workflow.
- Add recommendation/combinations/AI review generation to the scheduled pipeline if the dashboard should show fresh recommendation records after every worker run.

## Blockers

- No scheduled worker deployment blocker remains.
- Real repeated Misli collection still needs a safe public snapshot generation workflow before it replaces the deterministic fixture.

## Technical Debt

No code debt was introduced. Operational debt remains until the worker consumes fresh public/user-provided snapshots instead of the deterministic fixture.
