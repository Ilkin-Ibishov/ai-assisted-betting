# Task 39 - Live Run Registry

## Goal

Persist status and summary metrics for each live collection or live paper cycle run.

## Requirements

- Add a SQLite-backed live run registry.
- Track run type, provider, status, timing, item counts, and errors.
- Make writes idempotent enough for command retries.
- Expose repository/service helpers for later CLI and dashboard work.

## Implementation Notes

Recommended table fields:

```text
id
run_id
run_type
provider
league
season
status
started_at
finished_at
items_read
items_created
items_updated
items_skipped
errors_count
error_summary
model_name
created_at
```

Use the existing lightweight migration pattern.

## Acceptance Criteria

- Migration creates registry table for old and new databases.
- Unit tests cover starting, completing, and failing a run.
- Registry records survive process restarts.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

## Implementation Status

Completed in code:

```text
app/db/models.py
app/db/migrations.py
app/db/repositories.py
tests/unit/test_database.py
```

Implemented:

```text
live_runs SQLite table
003_create_live_runs migration
LiveRun ORM model
LiveRunRepository.start
LiveRunRepository.complete
LiveRunRepository.fail
LiveRunRepository.get_by_run_id
idempotent start by run_id
old database migration coverage
process restart persistence coverage
```

## Next

Task 40 - Manual Live Collection Commands.

## Blockers

None for Task 40. Misli-specific kickoff datetime validation remains a Task 40 import concern.

## Technical Debt

No JSON-file registry debt was introduced. The registry is SQLite-backed.
