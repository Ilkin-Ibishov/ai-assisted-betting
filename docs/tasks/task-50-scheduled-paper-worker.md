# Task 50 - Scheduled Paper Worker

## Goal

Add a safe recurring worker for paper-only live collection, prediction, settlement, and evaluation.

## Requirements

- Run only scoped paper-betting jobs.
- Never place real bets or automate bookmaker accounts.
- Use configurable cadence and provider enablement flags.
- Record every run in `live_runs`.
- Avoid overlapping executions.
- Surface stale data and failed runs to the dashboard.

## Acceptance Criteria

- Completed: worker can run once locally and under Railway-style environment variables with `LIVE_COLLECTION_ENABLED=true`.
- Completed: duplicate protection holds across repeated runs through existing collection/prediction/paper-bet identity rules.
- Completed: overlapping worker executions are skipped when another `scheduled_paper_worker` run is still `running`.
- Completed: failed provider collection is recorded on both the cycle run and worker run instead of placing real bets or crashing unrelated database state.
- Completed: dashboard status can see worker runs because every worker invocation records `live_runs.run_type='scheduled_paper_worker'`.

## Implementation Notes

- Added `app/services/scheduled_worker_service.py`.
- Added CLI command:

```powershell
python -m app.cli run-scheduled-paper-worker --provider misli-public --snapshot <snapshot.json> --model baseline_heuristic
```

- The command is one-shot, not a local infinite loop. Railway or another scheduler should invoke it on cadence.
- The worker refuses to run unless `LIVE_COLLECTION_ENABLED=true`.
- Settlement remains explicit and is not part of the scheduled worker yet.

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

Task 53 - Misli Live Scraper Hardening.

## Blockers

None for the completed one-shot worker. Railway cadence topology remains an open deployment decision for Tasks 51 and 60.

## Technical Debt

No new implementation debt. The worker intentionally delegates cadence to Railway or another external scheduler instead of embedding a long-running loop.
