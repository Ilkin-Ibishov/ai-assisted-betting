# Task 64 - Railway Dashboard Service

Status: in progress

## Goal

Deploy the React analytical dashboard as a public Railway service wired to the live Railway API.

## What Changed

- Added a dashboard-specific Dockerfile that builds the Vite app and serves it with Nginx.
- Added `dashboard/railway.json` so the dashboard service can use its own Dockerfile and `/` healthcheck.
- Added an Nginx template that listens on Railway's injected `PORT`.
- Made API CORS configurable and allowed Railway app dashboard origins for GET-only API access.
- Documented dashboard service configuration and CORS variables.

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
python -m app.cli production-smoke --api-base-url https://ai-assisted-betting-production.up.railway.app --dashboard-url https://<dashboard-service>.up.railway.app
```

## What's Next

- Create or configure the Railway dashboard service with root directory `dashboard`.
- Set `VITE_API_BASE_URL=https://ai-assisted-betting-production.up.railway.app`.
- Deploy and verify the public dashboard URL in a browser.

## Blockers

- Railway MCP tools are still not exposed in this Codex session, so service setup uses the Railway CLI.

## Technical Debt

No new code debt is intended. Continuous readiness still depends on a separate scheduled worker service after the dashboard is online.
