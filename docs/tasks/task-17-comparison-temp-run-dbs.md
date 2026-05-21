# Task 17 - Comparison Temporary Run Databases

## Goal

Harden replay comparison cleanup on Windows by avoiding project-local scratch SQLite cleanup during default runs.

## Problem

Comparison runs used to create per-run SQLite files under:

```text
data/comparisons/<report-name>/
```

and delete them after export. On Windows, SQLite files can remain locked briefly, making cleanup best-effort and occasionally leaving scratch DBs behind.

## Requirements

- Default `compare-replays` runs should use an OS temporary directory for scratch SQLite databases.
- `data/comparisons/<report-name>/source.csv` should still be retained for reproducibility.
- `--keep-run-dbs` should continue to preserve per-run SQLite files under:

```text
data/comparisons/<report-name>/
```

- Comparison JSON metadata should include `run_database_dir`.
  - `null` when run DBs are temporary and not retained.
  - `data/comparisons/<report-name>` when `--keep-run-dbs` is used.
- Database initialization should dispose its internal engine so transient SQLite handles are released promptly.

## Acceptance

Default comparison reports leave `source.csv` in the comparison directory and no `.sqlite` files.

With `--keep-run-dbs`, per-run `.sqlite` files remain under the comparison directory and the JSON metadata records their directory.

## Implementation Notes

Implemented in `app/services/comparison_service.py` and `app/db/migrations.py`.

What was done:

- Default comparison scratch DBs now live in a temporary directory.
- `--keep-run-dbs` keeps the existing auditable retained-DB behavior.
- Comparison metadata records `run_database_dir`.
- `init_db` now disposes its setup engine after migrations.
- Integration tests verify default runs leave no comparison `.sqlite` files and retained runs still keep them.

What's next:

- Evaluate whether comparison runs should be parallelized now that run DB isolation is cleaner.

Blockers:

- None.

Technical debt:

- The Windows cleanup debt is resolved for project-local comparison DBs.
- Comparison execution remains sequential and is tracked in `docs/agent/05_TECHNICAL_DEBT.md`.
