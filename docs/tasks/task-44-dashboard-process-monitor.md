# Task 44 - Dashboard Process Monitor

## Goal

Add a read-only dashboard view for live paper process status.

## Requirements

- Display latest live run status.
- Show provider, league, started/finished timestamps, counters, and errors.
- Show open paper bets awaiting settlement when available.
- Keep dashboard controls read-only.
- Add smoke coverage.

## UI Direction

Prefer an operational dashboard surface:

```text
Latest cycle status
Last successful collection
Errors and skipped records
Open paper bets
Recent run history
```

Do not make a marketing-style page.

## Acceptance Criteria

- Implemented: dashboard handles empty, success, and failure status shaping through tested live status helpers.
- Implemented: browser smoke verifies live process monitor rendering on desktop and mobile.
- Implemented: existing report analytics remain intact.

## Implementation Notes

Task 44 added:

```text
dashboard/src/lib/api.ts live status types and client
dashboard/src/lib/live.ts live process summary helper
dashboard/src/lib/live.test.ts empty/success/failure state coverage
dashboard/src/App.tsx read-only live process monitor panel
dashboard/scripts/dashboard-smoke.mjs live monitor assertions
```

The monitor shows:

```text
latest live run status
provider/source label
latest run counters
open and settled paper-bet counts
total live-run errors
last successful run
last failed run
```

It exposes no execution controls.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
cd dashboard
npm run test
npm run lint
npm run build
npm run smoke
```

## Next

Task 45 - End-To-End Live Paper Dry Run.

## Blockers

None for Task 44. Task 45 depends on the monitor and live API.

## Technical Debt

No new technical debt. The local dev database must be migrated with `init-db` before smoke if it was created before the `live_runs` table existed.
