# Railway Readiness

## Service Layout

Use four Railway services for the monitored staging deployment:

```text
postgres: Railway Postgres plugin
api: FastAPI backend
dashboard: Vite static frontend
worker: one-shot scheduled paper worker
```

The worker is separate from the API so API deploys and public health checks do not accidentally collect live data.

Task 60 deployment monitoring status:

```text
local production-smoke command implemented
Railway operator steps documented
worker freshness endpoint implemented
recommendation endpoint smoke implemented
deployed smoke requires real Railway service URLs and credentials
```

## API Service

The API service has repo-level Railway config in:

```text
railway.json
Dockerfile
```

Railway reads this config during deployment and the file overrides matching dashboard service settings for that deployment. Keep the API Railway service root at the repo root when using these files.

Builder:

```text
DOCKERFILE
```

The Dockerfile installs package dependencies into the final runtime image and starts the API through its `CMD`.

Legacy/manual Railpack build command:

```powershell
python -m pip install -e .
```

Dockerfile start command:

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
5. Confirm the API service uses `railway.json` and `Dockerfile`, or configure an equivalent Dockerfile deployment directly in Railway settings.
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

Task 50 implemented the one-shot worker command. Task 60 adds monitoring and production smoke checks for that worker.

Worker build command:

```powershell
python -m pip install -e .
```

Worker start command:

```powershell
python -m app.cli run-scheduled-paper-worker --provider misli-public --snapshot <snapshot.json> --model baseline_heuristic
```

Required worker-only variable:

```env
LIVE_COLLECTION_ENABLED=true
```

Recommended worker variables:

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
LIVE_COLLECTION_ENABLED=true
AI_ANALYSIS_MODE=deterministic
AI_ANALYSIS_MODEL_NAME=deterministic_ai_fallback
```

Keep API and dashboard services on:

```env
LIVE_COLLECTION_ENABLED=false
```

Cadence guidance:

- Use Railway cron or an equivalent scheduler to invoke the one-shot worker.
- Start conservatively, for example every 30 to 60 minutes.
- Avoid overlapping runs. The worker skips when another `scheduled_paper_worker` run is still `running`.
- Keep snapshots public/user-provided and paper-only. Do not add login automation, account actions, CAPTCHA/bot bypass, proxy evasion, or real-money betting.

Worker monitoring endpoint:

```text
GET /api/live/worker-status
GET /api/live/worker-status?fresh_after_minutes=90
```

Healthy response shape:

```json
{
  "status": "fresh",
  "healthy": true,
  "freshness_minutes": 24,
  "fresh_after_minutes": 90,
  "latest_worker_run": {
    "run_type": "scheduled_paper_worker",
    "status": "completed"
  }
}
```

Unhealthy statuses:

```text
never_run
stale
failed
running
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
GET /api/live/worker-status
GET /api/live/recommendations?limit=5
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
curl https://<api-service>.up.railway.app/api/live/worker-status
curl https://<api-service>.up.railway.app/api/operations/guardrails
curl https://<api-service>.up.railway.app/api/live/recommendations?limit=5
curl https://<api-service>.up.railway.app/api/reports/comparisons
```

## Operational Guardrails

Task 61 added:

```text
GET /api/operations/guardrails
python -m app.cli operational-status
```

Overall status values:

```text
ok
warning
critical
```

Guardrail meanings:

- `worker_freshness`: warns when the worker never ran, is stale, or is still running; critical when the latest worker failed.
- `repeated_worker_failures`: critical when consecutive failed worker runs meet the configured threshold.
- `provider_data_quality`: warns for Misli parser drift, stale snapshots, low extraction confidence, or unresolved kickoff-date failures.
- `ai_eval_safety`: critical when an AI advisory output failed evals or has an `ai_eval_failed` risk flag.
- `recommendation_output`: warns when a fresh worker cycle produces zero paper recommendations.

What to check next:

- Worker issues: Railway worker logs, cron cadence, `DATABASE_URL`, and `LIVE_COLLECTION_ENABLED=true` on the worker only.
- Provider issues: collect a fresh public/user-provided snapshot and inspect parser confidence.
- AI eval issues: keep deterministic fallback active and review the failed `ai_analysis_runs` output.
- Empty recommendation issues: inspect odds movement, provider health, recommendation thresholds, and AI review state.

Do not add notification bots until this API/dashboard guardrail status is stable in staging.

## Failure Triage

Worker freshness:

- `never_run`: Railway cron has not invoked the worker, the worker service is not deployed, or `DATABASE_URL` points to a different database than the API.
- `stale`: the worker has not completed within `fresh_after_minutes`; inspect worker deploy logs and Railway cron cadence.
- `failed`: inspect `latest_worker_run.error_summary`; common causes are provider parser drift, missing snapshot file, `LIVE_COLLECTION_ENABLED=false`, or database connectivity.
- `running`: a worker is currently active or a previous run was interrupted before marking completion.

Recommendation endpoint:

- Empty response can be valid immediately after deploy.
- Repeated empty response after fresh worker runs means the pipeline produced no eligible recommendations; inspect `/api/live/odds-movement`, provider health, and recommendation risk flags.

AI review:

- If `GET /api/ai/recommendation-review/latest` is missing, run `python -m app.cli analyze-recommendations` after recommendations exist.
- AI review remains advisory and does not execute bets.

## Rollback And Recovery

Rollback order:

1. Roll back the last failed Railway deployment for the affected service.
2. Confirm API `/api/health` before dashboard checks.
3. Rebuild the dashboard if the API URL changed.
4. Keep API and dashboard `LIVE_COLLECTION_ENABLED=false` while recovering API or database health.
5. Pause worker scheduling if Postgres, provider parsing, or recommendation endpoints are unhealthy.
6. If Postgres is unhealthy, inspect Railway Postgres logs before running any collection command.

Recovery notes:

- `python -m app.cli init-db` is idempotent for fresh staging databases.
- Do not delete Postgres data to fix schema issues without an explicit backup.
- Dashboard failures are usually build-time API URL or static publish-directory issues.
- API failures are usually missing `DATABASE_URL`, dependency install failure, or Postgres connectivity.

Keep all live workflows paper-only. Scheduled collection is allowed only through the separate monitored worker service.

## Readiness Report

The final Task 62 readiness decision is documented in:

```text
docs/deployment/production-readiness-review.md
```

Current decision:

```text
conditionally ready for continuous paper-only Railway staging
```

Full production proof is pending until deployed Railway smoke passes against real service URLs.

## Current Railway Link

The local Railway CLI has been linked to:

```text
project: dynamic-unity
environment: production
service: ai-assisted-betting
```

Current deploy triage:

```text
Railpack detected Python but failed because no start command was configured.
railway.json now supplies the API build command, start command, healthcheck, and restart policy.
The first Railpack config-as-code attempt built successfully but the runtime image crashed with ModuleNotFoundError: No module named 'typer'.
The API service now uses an explicit Dockerfile so dependencies are installed in the final runtime image.
The Dockerfile-backed API deployment for commit ad00259 succeeded and Railway healthcheck returned 200.
Railway Postgres was added, and the API service `DATABASE_URL` now references the Railway Postgres service.
The first Postgres-backed redeploy failed because Railway supplies `postgresql://...`, which SQLAlchemy maps to the missing `psycopg2` driver by default.
The database engine now normalizes plain `postgresql://...` URLs to `postgresql+psycopg://...` so the installed `psycopg` driver is used.
```

Next operational checks:

1. Push the Postgres URL normalization fix and wait for Railway redeploy.
2. Confirm `/api/health` succeeds while using Railway Postgres.
3. Add the scheduled worker service and run it at least once.
4. Rerun `python -m app.cli production-smoke --api-base-url https://ai-assisted-betting-production.up.railway.app`.

Current API URL:

```text
https://ai-assisted-betting-production.up.railway.app
```

Current deployed smoke result:

```text
/api/health: 200 {"status":"ok","database":"ok"}
/api/live/status: 200, no live runs yet
/api/live/worker-status: 200 {"status":"never_run","healthy":false}
production-smoke: fails at worker_status until the worker has run
```
