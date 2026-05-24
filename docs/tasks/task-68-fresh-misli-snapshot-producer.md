# Task 68 - Fresh Misli Snapshot Producer

Status: completed locally, pending Railway service wiring

## Goal

Create the missing source step between Misli.az public football pages and the scheduled worker so the system can produce fresh read-only snapshot JSON and make it available through the API for `WORKER_SNAPSHOT_URL`.

## What Changed

- Added database-backed latest snapshot storage through `live_snapshots`.
- Added API endpoints:
  - `POST /api/live/snapshots/latest/{provider}` stores the newest provider snapshot behind a bearer token.
  - `GET /api/live/snapshots/latest/{provider}` serves the latest raw snapshot JSON for the worker.
- Added `SNAPSHOT_INGEST_TOKEN` configuration. Snapshot ingest is unavailable until this token is configured.
- Extended `tools/misli-public-snapshot.mjs` with:
  - `--post-url`
  - `--token`
  - `SNAPSHOT_INGEST_TOKEN` fallback
  - strict post URL validation for the API latest-snapshot endpoint
- Added `Dockerfile.snapshot`, a browser-enabled Node/Playwright image for a dedicated snapshot producer service.
- Updated `.env.example` so API, worker, and producer variables show the intended Railway flow.
- Added snapshot producer tests for unsafe post URLs and missing tokens.

## Intended Railway Flow

```text
Misli.az public football page
-> snapshot producer service
-> POST /api/live/snapshots/latest/misli-public
-> API stores latest JSON in Postgres
-> worker reads WORKER_SNAPSHOT_URL
-> recommendations, combinations, AI review
-> daily dashboard
```

## Verification

Completed local verification:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
cd dashboard
npm run snapshot:test
npm run test
npm run lint
npm run build
$env:PLAYWRIGHT_CHANNEL='chrome'; npm run smoke
```

Result:

```text
Backend tests: 168 passed
Ruff: all checks passed
Snapshot producer tests: 2 passed
Dashboard tests: 29 passed
Dashboard lint: passed
Dashboard build: passed
Dashboard smoke: passed
```

## Railway Usage

API service:

```env
SNAPSHOT_INGEST_TOKEN=<secret>
```

Worker service:

```env
WORKER_SNAPSHOT_URL=https://ai-assisted-betting-production.up.railway.app/api/live/snapshots/latest/misli-public
```

Snapshot producer service:

```env
SNAPSHOT_SOURCE_URL=https://www.misli.az/idman-novleri/futbol
SNAPSHOT_SPORT=football
SNAPSHOT_POST_URL=https://ai-assisted-betting-production.up.railway.app/api/live/snapshots/latest/misli-public
SNAPSHOT_INGEST_TOKEN=<same-secret-as-api>
```

## What's Next

- Deploy and schedule the dedicated snapshot producer on Railway.
- Run an end-to-end proof where the producer posts a fresh snapshot, the worker consumes the API snapshot URL, and the dashboard shows fresh daily recommendations.
- Add richer team, league, player, injury, lineup, and schedule research sources after the fresh odds loop is proven.

## Blockers

- The producer service still needs Railway service creation/scheduling and secret configuration.
- Recommendation quality remains odds-first until richer football context sources are integrated.

## Technical Debt

The current producer captures public Misli list-page odds only. It does not yet enrich matches with current club form, league table position, player availability, expected lineups, injuries, or schedule congestion.
