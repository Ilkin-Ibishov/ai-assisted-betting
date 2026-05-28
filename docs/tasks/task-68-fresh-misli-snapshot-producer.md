# Task 68 - Fresh Misli Snapshot Producer

Status: completed and deployed

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
- Added `Dockerfile.snapshot`, a browser-enabled Playwright image for a dedicated snapshot producer service. Task 70 later switched it to the official Playwright base image for more reliable Railway builds.
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

## Railway Proof

- Created Railway service `snapshot-producer`.
- Deployed `Dockerfile.snapshot` with cron schedule `*/30 * * * *`.
- Configured API `SNAPSHOT_INGEST_TOKEN`, producer `SNAPSHOT_POST_URL`, and worker `WORKER_SNAPSHOT_URL`.
- Ran one producer cycle with Railway environment variables.
- Verified `GET /api/live/snapshots/latest/misli-public` returned:

```text
status=200
event_count=21
source=misli_public
```

The first worker proof consumed that snapshot URL but failed on one bare `HH:MM` kickoff row. Task 69 resolves that parser gap.

Snapshot producer service:

```env
SNAPSHOT_SOURCE_URL=https://www.misli.az/idman-novleri/futbol
SNAPSHOT_SPORT=football
SNAPSHOT_POST_URL=https://ai-assisted-betting-production.up.railway.app/api/live/snapshots/latest/misli-public
SNAPSHOT_INGEST_TOKEN=<same-secret-as-api>
```

## What's Next

- Deploy Task 69 and run an end-to-end proof where the worker consumes the fresh API snapshot URL and the dashboard shows fresh daily recommendations.
- Add richer team, league, player, injury, lineup, and schedule research sources after the fresh odds loop is proven.

## Blockers

- The producer service exists on Railway and has scheduling/secret configuration. Task 70 completed the latest producer image redeploy proof.
- Recommendation quality remains odds-first until richer football context sources are integrated.

## Technical Debt

The current producer captures public Misli list-page odds only. It does not yet enrich matches with current club form, league table position, player availability, expected lineups, injuries, or schedule congestion.
