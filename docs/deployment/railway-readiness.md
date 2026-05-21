# Railway Readiness

## Service Layout

Use three Railway services for the first staging deployment:

```text
postgres: Railway Postgres plugin
api: FastAPI backend
dashboard: Vite static frontend
```

Add the scheduled worker only after Task 50.

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

After deploy:

```powershell
curl https://<api-service>.up.railway.app/api/health
python -m app.cli show-config
```

Expected health payload:

```json
{"status":"ok","database":"ok"}
```

Keep all live workflows paper-only. Do not add scheduled collection until Task 50.
