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

- Confirm the GitHub-triggered Railway deployment reaches a healthy state.
- Add or connect Railway Postgres so `DATABASE_URL` is durable instead of falling back to ephemeral SQLite.
- Run deployed `production-smoke` after a public API domain exists.

## Blockers

- Railway MCP tools are not exposed in the current Codex session. The project is connected through the Railway CLI instead.
- Deployed smoke cannot run until the Dockerfile-backed Railway deployment is successful and a reachable API URL exists.

## Technical Debt

No new code debt was introduced. Operational readiness still depends on Railway Postgres, a public API domain, and deployed smoke evidence.
