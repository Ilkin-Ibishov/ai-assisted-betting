# Task 64 - Railway Dashboard Service

Status: completed

## Goal

Deploy the React analytical dashboard as a public Railway service wired to the live Railway API.

## What Changed

- Added a dashboard-specific Dockerfile that builds the Vite app and serves it with Nginx.
- The dashboard Dockerfile uses `npm install` during Railway image build because npm 11 rejected the existing cross-platform optional-dependency lock entries under `npm ci` in the Linux builder.
- Added `dashboard/railway.json` so the dashboard service can use its own Dockerfile and `/` healthcheck.
- Added an Nginx template that listens on Railway's injected `PORT`.
- Made API CORS configurable and allowed Railway app dashboard origins for GET-only API access.
- Documented dashboard service configuration and CORS variables.
- Created a Railway `dashboard` service.
- Set `VITE_API_BASE_URL=https://ai-assisted-betting-production.up.railway.app` on the dashboard service.
- Deployed the dashboard folder to Railway with `railway up . --path-as-root --service dashboard`.
- Generated the public dashboard domain `https://dashboard-production-0a69.up.railway.app`.

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

Completed deployment verification:

```text
dashboard URL: https://dashboard-production-0a69.up.railway.app
dashboard deployment: SUCCESS
production-smoke with dashboard_url: passed
rendered browser check: React root mounted, API requests reached the live Railway API
```

## What's Next

- Add the dedicated Railway scheduled worker service with cron.
- Consider running recommendation review analysis after fresh recommendation output exists so the dashboard AI review panels have live records instead of nullable 404 responses.

## Blockers

- No dashboard deployment blocker remains.
- Railway MCP tools are still not exposed in this Codex session, so service setup used the Railway CLI.

## Technical Debt

No new code debt was introduced. Continuous readiness still depends on a separate scheduled worker service after the dashboard is online.
