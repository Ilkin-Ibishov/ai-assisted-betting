# Task 40 - Manual Live Collection Commands

## Goal

Implement manual commands for collecting upcoming matches and current odds through the live provider contract.

## Requirements

- Implement or complete `collect-matches`.
- Implement or complete `collect-odds`.
- Persist normalized matches and odds through existing services/repositories.
- Record live run registry entries.
- Keep commands idempotent.
- Add a manual Misli snapshot collection/import path after Task 38 DTO validation exists.

## Implementation Notes

Initial provider target is Misli.az public allowed football data via the public snapshot prototype:

```powershell
node tools\misli-public-snapshot.mjs --out data\misli-public-snapshot.sample.json
```

The CLI should consume validated snapshot JSON rather than embedding scraping directly in Python first. This keeps browser collection inspectable and lets provider DTO validation fail closed before database writes.

Command shape:

```powershell
python -m app.cli collect-matches --provider <provider> --league <league> --lookahead-hours 72
python -m app.cli collect-odds --provider <provider> --league <league>
python -m app.cli collect-matches --provider misli-public --snapshot data\misli-public-snapshot.sample.json
python -m app.cli collect-odds --provider misli-public --snapshot data\misli-public-snapshot.sample.json
```

Import rules:

```text
matches: require full kickoff datetime before inserting
odds: require existing imported match and complete 1X2 HOME/DRAW/AWAY odds
invalid events: skip and record structured run errors
snapshot raw payload: preserve for audit
```

## Acceptance Criteria

- Commands print standard counters.
- Duplicate command runs do not duplicate matches or odds snapshots beyond allowed snapshot uniqueness.
- Provider errors are recorded in live run registry.
- Tests cover success, partial failure, and idempotent rerun.
- Misli snapshot import refuses records without full kickoff datetime.
- Misli snapshot import refuses incomplete 1X2 odds.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

## Implementation Status

Completed in code:

```text
app/services/live_collection_service.py
app/cli.py
tests/unit/test_live_collection_service.py
tests/integration/test_cli.py
```

Implemented:

```text
collect-matches --provider misli-public --snapshot <path>
collect-odds --provider misli-public --snapshot <path>
validated Misli snapshot JSON consumption
idempotent match import
idempotent odds import
SQLite live_run records for completed and failed imports
fail-closed missing kickoff date handling
fail-closed incomplete HOME/DRAW/AWAY 1X2 odds handling
```

Manual check against the current public Misli snapshot:

```text
items_read=28
items_created=0
items_skipped=28
errors_count=28
```

This is expected until the snapshot tool can provide full kickoff dates or a validated date fallback exists.

## Next

Task 41 - Live Paper Cycle Orchestrator.

## Blockers

Misli.az public odds are accessible, but kickoff datetime extraction is incomplete in the current prototype. The implemented commands reject these records and record failed live runs instead of importing incomplete matches.

## Technical Debt

Track DOM selector dependence and kickoff datetime fallback assumptions. No JSON-file registry debt was introduced.
