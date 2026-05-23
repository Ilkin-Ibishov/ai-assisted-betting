# Task 63 - Railway API Config As Code

Status: completed

## Goal

Fix the first Railway API deployment failure by making the service start command explicit in the repository.

## What Changed

- Added `railway.json` with Railpack builder, editable Python install build command, API start command, `/api/health` healthcheck, and restart policy.
- Updated Railway readiness docs with the linked project/environment/service and the current deploy triage.
- Switched the API service to an explicit Dockerfile after Railway's Railpack runtime crashed with `ModuleNotFoundError: No module named 'typer'`.
- Kept `/api/health`, restart policy, and timeout in `railway.json`, while the Dockerfile owns dependency installation and process startup.
- Updated the Dockerfile to create runtime `data` and `reports` directories instead of copying local/generated directories that may not exist in the Git build context.
- Deployed commit `ad00259` to Railway successfully; Railway healthcheck hit `/api/health` with 200.
- Generated Railway public API domain: `https://ai-assisted-betting-production.up.railway.app`.
- Added Railway Postgres and set the API `DATABASE_URL` to the Railway Postgres reference.
- Added database URL normalization so Railway's plain `postgresql://...` URL uses the installed SQLAlchemy `psycopg` driver instead of defaulting to missing `psycopg2`.
- Redacted CLI database URL output for `init-db` and `show-config` so Railway deployment logs do not print credentials.
- Confirmed the Postgres-backed Railway API deployment for commit `e129e8a` is healthy.
- Installed Railway agent tooling with `railway setup agent -y`; restart Codex if the Railway MCP server is not visible in the active tool list.
- After Codex restart, confirmed the Railway skill remains available but no dedicated Railway MCP namespace is exposed in the active tool list; Railway operations continue through the linked Railway CLI.
- Ran a one-off scheduled paper worker against Railway Postgres using the Postgres public database URL because `railway run` injects Railway's private Postgres hostname, which is only resolvable inside Railway networking.
- Confirmed `/api/live/worker-status` is fresh and deployed `production-smoke` passes against `https://ai-assisted-betting-production.up.railway.app`.

## Verification

Run after implementation:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
cd dashboard
npm run test
npm run lint
npm run build
$env:PLAYWRIGHT_CHANNEL='chrome'; npm run smoke
```

Then deploy:

```powershell
git push
railway logs --service ai-assisted-betting --environment production --lines 100
```

## What's Next

- Add a dedicated scheduled worker service with Railway cron.
- Decide whether to implement service roles or a worker-specific Railway service config so the API `railway.json` healthcheck/startup does not accidentally apply to worker deployments.
- Add the Railway dashboard service and run smoke with `--dashboard-url`.

## Blockers

- No API deployment blocker remains.
- Railway MCP tooling is configured locally, but this restarted Codex session still does not expose a dedicated Railway MCP namespace.
- Continuous worker proof is pending because the current worker run was one-off, not Railway cron-managed.

## Technical Debt

No new code debt was introduced. Operational readiness still depends on a dedicated scheduled worker deployment, dashboard service deployment, and smoke evidence that includes the deployed dashboard URL.
