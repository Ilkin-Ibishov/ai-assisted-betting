# Task 69 - Misli Bare-Time Resolution

Status: completed and deployed; end-to-end fresh loop proof still pending

## Goal

Unblock fresh Misli worker runs when the public football page emits a kickoff label as bare `HH:MM` with no explicit `Bu Gun` or `Sabah` prefix.

## What Changed

- `MisliPublicSnapshot` now resolves bare `HH:MM` kickoff labels against the snapshot `scraped_at` date in `Asia/Baku`.
- Rows still fail closed when no valid `scraped_at` timestamp exists or kickoff time is empty.
- Updated live provider and live collection tests so the intended policy is explicit:
  - `Bu Gun HH:MM` -> scraped local date
  - `Sabah HH:MM` -> scraped local date plus one day
  - bare `HH:MM` -> scraped local date
  - empty or unresolvable datetime -> reject
- Updated the provider-health advisory text so agents no longer assume bare times are always rejected.

## Production Finding

The first fresh Railway proof after Task 68 succeeded through producer -> API latest snapshot endpoint, but the worker failed on a live Misli row with bare `03:00`:

```text
cycle.collect_matches.items_read=21
cycle.collect_matches.items_created=20
cycle.collect_matches.errors_count=1
cycle.status=failed
snapshot_path=data/live-snapshots/scheduled-worker-...json
```

This task fixes that parser gap.

## Verification

Completed checks:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_live_provider_contract.py tests\unit\test_live_collection_service.py tests\integration\test_cli.py::test_manual_live_collection_command_records_misli_validation_errors -q
.\.venv\Scripts\python.exe -m ruff check app\providers\misli_public.py app\services\ai_analysis_service.py tests\unit\test_live_provider_contract.py tests\unit\test_live_collection_service.py tests\integration\test_cli.py
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
Targeted tests: 16 passed
Targeted Ruff: all checks passed
Backend tests: 168 passed
Ruff: all checks passed
Snapshot producer tests: 2 passed
Dashboard tests: 29 passed
Dashboard lint: passed
Dashboard build: passed
Dashboard smoke: passed
```

## What's Next

- Trigger or wait for the worker to consume a fresh Task 70 snapshot and verify the live cycle completes.

## Blockers

- No parser blocker remains for bare `HH:MM` Misli rows.
- The current operational blocker is waiting for the next Railway worker run to consume the fresh Task 70 snapshot.

## Technical Debt

Bare times are resolved to the scraped local date. This is practical for the public football list because the page is an upcoming-event view, but richer date group extraction from the rendered DOM would still be a stronger long-term source of truth.
