# Task 67 - Fresh Snapshot Worker Input

Status: completed

## Goal

Let the scheduled worker consume a fresh public/user-provided Misli snapshot JSON instead of being locked to the bundled deterministic fixture, and refresh the daily recommendation outputs after each successful worker cycle.

## What Changed

- Added `--snapshot-url` to `run-scheduled-paper-worker`.
- Added `WORKER_SNAPSHOT_URL` support to `Dockerfile.worker`.
- The worker now resolves input in this order:
  - if `WORKER_SNAPSHOT_URL` / `--snapshot-url` is present, download HTTPS JSON into `data/live-snapshots/`
  - otherwise use `WORKER_SNAPSHOT` / `--snapshot`
- Snapshot URL downloads are constrained to HTTPS JSON responses and capped at 5 MB.
- After a successful scheduled paper cycle, the worker now automatically runs:
  - recommendation generation
  - combination generation
  - deterministic AI recommendation review
- Worker CLI output now includes:
  - `snapshot_path`
  - `recommendations.created`
  - `combinations.created`
  - `ai_review_id`
- Added tests for normal snapshot-path operation and fresh snapshot URL operation.

## Verification

Completed checks:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
cd dashboard
npm run test
npm run lint
npm run build
$env:PLAYWRIGHT_CHANNEL='chrome'; npm run smoke
```

Result:

```text
Backend tests: 166 passed
Ruff: all checks passed
Dashboard tests: 29 passed
Dashboard lint: passed
Dashboard build: passed
Dashboard smoke: passed
```

## Railway Usage

To use a fresh externally hosted snapshot JSON in Railway, set:

```env
WORKER_SNAPSHOT_URL=https://<public-or-user-provided-host>/misli/latest.json
WORKER_LEAGUE=fresh-snapshot
```

Keep `WORKER_SNAPSHOT` unset or leave it as fallback. If `WORKER_SNAPSHOT_URL` is absent, the worker still uses the deterministic fixture path configured by `WORKER_SNAPSHOT`.

## What's Next

- Build the next source step: a browser-enabled snapshot producer that periodically creates the Misli snapshot JSON and publishes it somewhere the worker can fetch.
- Add richer team/league/player research sources before treating recommendation quality as product-complete.

## Blockers

- No blocker remains for worker consumption of fresh HTTPS JSON snapshots.
- Direct Misli Playwright collection inside the Railway worker still requires a browser-enabled worker image or a separate snapshot producer job/service.

## Technical Debt

The deterministic fixture fallback remains for safety and deployment proof. The system still needs a dedicated fresh snapshot producer to move from "can consume fresh snapshots" to "fully self-refreshing Misli ingestion."
