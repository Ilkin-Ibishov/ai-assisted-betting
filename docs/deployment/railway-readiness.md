# Railway Readiness

## Service Layout

Use three Railway services for the first staging deployment:

```text
postgres: Railway Postgres plugin
api: FastAPI backend
dashboard: Vite static frontend
```

Add the scheduled worker only after Task 50.

Task 51 deployment runbook status:

```text
local production-smoke command implemented
Railway operator steps documented
deployed smoke requires real Railway service URLs and credentials
```

## API Service

Build command:

```powershell
python -m pip install -e .
```

Start command:

```powershell
python -m app.cli init-db && python -m uvicorn app.api:api --host 0.0.0.0 --port $PORT
```

Health check path:

```text
/api/health
```

Deploy notes:

1. Create or select a Railway project.
2. Add a Railway Postgres database.
3. Add an API service from the GitHub repo.
4. Set the API root directory to the repo root.
5. Configure the build and start commands above.
6. Add the required variables below.
7. Deploy and confirm `/api/health` returns `{"status":"ok","database":"ok"}`.

Required variables:

```env
DATABASE_URL=${{Postgres.DATABASE_URL}}
DEFAULT_SPORT=football
DEFAULT_MARKET=1X2
DEFAULT_STAKE_UNITS=1.0
MIN_EDGE=0.07
MIN_ODDS=1.70
MAX_ODDS=3.50
FEATURE_VERSION=v0_baseline
MODEL_NAME=baseline_heuristic
MODEL_VERSION=v0
ELO_INITIAL_RATING=1500
ELO_K_FACTOR=20
ELO_HOME_ADVANTAGE=65
LOG_LEVEL=INFO
LIVE_COLLECTION_ENABLED=false
AI_ANALYSIS_MODE=deterministic
AI_ANALYSIS_MODEL_NAME=deterministic_ai_fallback
```

## Dashboard Service

Build command:

```powershell
cd dashboard && npm ci && npm run build
```

Publish directory:

```text
dashboard/dist
```

Required variable:

```env
VITE_API_BASE_URL=https://<api-service>.up.railway.app
```

When `VITE_API_BASE_URL` is empty, the dashboard keeps using local relative `/api` paths and the Vite dev proxy.

Deploy notes:

1. Add a dashboard service from the same GitHub repo.
2. Set the build command to `cd dashboard && npm ci && npm run build`.
3. Set the publish directory to `dashboard/dist`.
4. Set `VITE_API_BASE_URL` to the deployed API base URL without a trailing `/api`.
5. Redeploy whenever the API URL changes because Vite injects this value at build time.

## Scheduled Worker Service

Task 50 implemented the one-shot worker command, but Task 51 does not enable scheduled production collection by default.

Use this only after Task 60 monitoring is in place:

```powershell
python -m app.cli run-scheduled-paper-worker --provider misli-public --snapshot <snapshot.json> --model baseline_heuristic
```

Required worker-only variable:

```env
LIVE_COLLECTION_ENABLED=true
```

Keep API and dashboard services on:

```env
LIVE_COLLECTION_ENABLED=false
```

## Postgres Notes

Fresh Postgres databases are created through SQLAlchemy models via:

```powershell
python -m app.cli init-db
```

Legacy schema migrations in `app/db/migrations.py` remain SQLite-only because they upgrade old local SQLite files. For non-SQLite databases, Task 49 records those migration names as no-op model-managed migrations after `Base.metadata.create_all`.

Postgres driver:

```text
psycopg[binary]
```

## Staging Smoke

After deploy, run the production smoke command from a local checkout or Railway shell:

```powershell
python -m app.cli production-smoke --api-base-url https://<api-service>.up.railway.app --dashboard-url https://<dashboard-service>.up.railway.app
```

The smoke command verifies:

```text
GET /api/health
GET /api/live/status
GET /api/live/runs?limit=5
GET /api/reports/comparisons
dashboard HTML root
```

Expected health portion:

```json
{"status":"ok","database":"ok"}
```

If only the API exists, omit `--dashboard-url`.

Useful manual checks:

```powershell
curl https://<api-service>.up.railway.app/api/health
curl https://<api-service>.up.railway.app/api/live/status
curl https://<api-service>.up.railway.app/api/reports/comparisons
```

## Rollback And Recovery

Rollback order:

1. Roll back the last failed Railway deployment for the affected service.
2. Confirm API `/api/health` before dashboard checks.
3. Rebuild the dashboard if the API URL changed.
4. Keep `LIVE_COLLECTION_ENABLED=false` while recovering API or database health.
5. If Postgres is unhealthy, pause worker scheduling and inspect Railway Postgres logs before running any collection command.

Recovery notes:

- `python -m app.cli init-db` is idempotent for fresh staging databases.
- Do not delete Postgres data to fix schema issues without an explicit backup.
- Dashboard failures are usually build-time API URL or static publish-directory issues.
- API failures are usually missing `DATABASE_URL`, dependency install failure, or Postgres connectivity.

Keep all live workflows paper-only. Do not enable scheduled collection until Task 60 monitoring is implemented.
