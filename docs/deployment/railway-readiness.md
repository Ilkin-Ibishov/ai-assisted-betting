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
deployed smoke passed against the Railway API after a one-off paper worker run
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
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
CORS_ALLOWED_ORIGIN_REGEX=^(http://(localhost|127\.0\.0\.1):\d+|https://[a-z0-9-]+\.up\.railway\.app)$
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
2. Set the service root directory to `dashboard`.
3. Use `dashboard/railway.json` and `dashboard/Dockerfile` for the static build/runtime.
4. Set `VITE_API_BASE_URL` to the deployed API base URL without a trailing `/api`.
5. Redeploy whenever the API URL changes because Vite injects this value at build time.

Dashboard service files:

```text
dashboard/railway.json
dashboard/Dockerfile
dashboard/nginx.conf.template
```

Current dashboard URL:

```text
https://dashboard-production-0a69.up.railway.app
```

Current dashboard deployment notes:

```text
The dashboard service was created as an empty Railway service and deployed with `railway up . --path-as-root --service dashboard` from the `dashboard/` directory.
The GitHub repo-link creation path returned an OAuth authorization error from the Railway CLI, so dashboard deployments currently use explicit CLI uploads.
```

## Scheduled Worker Service

Task 50 implemented the one-shot worker command. Task 60 adds monitoring and production smoke checks for that worker.

Worker build command:

```powershell
python -m pip install -e .
```

Worker Dockerfile:

```text
Dockerfile.worker
```

Worker start command:

```powershell
python -m app.cli run-scheduled-paper-worker --provider misli-public --snapshot <snapshot.json> --model baseline_heuristic
```

Fresh snapshot URL form:

```powershell
python -m app.cli run-scheduled-paper-worker --provider misli-public --snapshot-url https://<host>/misli/latest.json --model baseline_heuristic
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
WORKER_PROVIDER=misli-public
WORKER_SNAPSHOT=docs/fixtures/task45-live-dry-run-snapshot.json
# Prefer WORKER_SNAPSHOT_URL when a fresh public/user-provided JSON snapshot is available.
# WORKER_SNAPSHOT_URL=https://<host>/misli/latest.json
WORKER_MODEL=baseline_heuristic
WORKER_LEAGUE=railway-fixture
WORKER_SEASON=2026
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
- The initial Railway cron proof may use the deterministic Task 45 fixture. For fresh data coverage, set `WORKER_SNAPSHOT_URL` to an HTTPS JSON snapshot generated by a safe public/user-provided snapshot producer. The worker consumes that JSON and refreshes recommendations, combinations, and AI review after a successful cycle.

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

Railway API and Postgres proof is complete for the current single-service deployment. Continuous worker proof is pending until a dedicated scheduled worker service is created.

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
CLI database URL output is redacted so Railway logs do not print database credentials.
The Postgres-backed API deployment for commit e129e8a succeeded; `/api/health` returns 200 with `{"status":"ok","database":"ok"}`.
Railway agent tooling was installed through `railway setup agent -y`; Codex may need a restart before the Railway MCP server appears in the active tool list.
After Codex restart, the Railway skill remains installed but no dedicated Railway MCP namespace is exposed in the active tool list; Railway operations continue through the linked Railway CLI.
A one-off scheduled paper worker was run locally against Railway Postgres using the Postgres public database URL because `railway run` injects the private `postgres.railway.internal` hostname, which does not resolve from the local machine.
The one-off worker completed with 1 collected match, 3 odds snapshots, 3 features, 3 predictions, and 1 paper bet.
Production smoke passed against `https://ai-assisted-betting-production.up.railway.app`.
The dedicated Railway `worker` service was created, deployed with `Dockerfile.worker`, and configured with cron schedule `*/30 * * * *`.
The cron-triggered worker run at `2026-05-24T14:01:20Z` completed and refreshed `/api/live/worker-status`.
Task 67 commit `b1faa48` deployed successfully to the API service through GitHub. The updated worker image was deployed through Railway upload deployment `95a519c2-3c27-4d33-b6f5-755b866bd77a` after recreating the worker upload `railway.json` without a UTF-8 BOM. Production smoke passed after the deploy.
Task 68 added the API latest-snapshot endpoints and `Dockerfile.snapshot` for a dedicated Playwright producer service.
Task 68 Railway wiring created `snapshot-producer`, deployed it with `Dockerfile.snapshot`, configured a `*/30 * * * *` schedule, and posted a fresh 21-event Misli snapshot through the API latest-snapshot endpoint. The first worker proof consumed that URL but failed on a bare `HH:MM` row; Task 69 resolves that parser gap and the API/worker images were redeployed. A later producer upload using the browser-installing image exported successfully but stayed as a stopped `BUILDING` deployment, so Task 70 switched the producer to the official Playwright base image. Deployment `df944e43-9e2c-4bad-9b1f-0c582f4e5e37` is successful and an immediate producer run posted a fresh 21-event snapshot with `scraped_at=2026-05-28T00:05:28.437Z`.
```

Next operational checks:

1. Confirm the scheduled worker consumes the fresh Task 70 snapshot.
2. Confirm producer -> API latest snapshot -> worker -> dashboard end-to-end freshness.
3. Add richer current league, team, player, injury, lineup, and schedule sources for recommendation quality.

Snapshot producer service variables:

```env
SNAPSHOT_SOURCE_URL=https://www.misli.az/idman-novleri/futbol
SNAPSHOT_SPORT=football
SNAPSHOT_POST_URL=https://ai-assisted-betting-production.up.railway.app/api/live/snapshots/latest/misli-public
SNAPSHOT_INGEST_TOKEN=<same-secret-as-api>
```

API service variable:

```env
SNAPSHOT_INGEST_TOKEN=<secret>
```

Worker service variable:

```env
WORKER_SNAPSHOT_URL=https://ai-assisted-betting-production.up.railway.app/api/live/snapshots/latest/misli-public
```

Current API URL:

```text
https://ai-assisted-betting-production.up.railway.app
```

Current deployed smoke result:

```text
/api/health: 200 {"status":"ok","database":"ok"}
/api/live/status: 200, latest worker run completed, open_paper_bets=1
/api/live/worker-status: 200 {"status":"fresh","healthy":true}
production-smoke: passed against https://ai-assisted-betting-production.up.railway.app
production-smoke with dashboard URL: passed against https://dashboard-production-0a69.up.railway.app
Railway cron worker: completed run started at 2026-05-24T14:01:20Z
Task 67 worker image deploy: SUCCESS
Task 70 snapshot producer image deploy: SUCCESS
latest Misli snapshot scraped_at: 2026-05-28T00:05:28.437Z
latest API logs redact the database password
```
