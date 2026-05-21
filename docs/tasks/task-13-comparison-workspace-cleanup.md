# Task 13 - Comparison Workspace Cleanup And Metadata

## Goal

Keep replay comparison runs clean, reproducible, and easier to scale.

## Problem

`compare-replays` currently creates scratch SQLite files directly under `data/` and keeps them forever. It also does not write enough comparison metadata to reproduce the experiment from the comparison JSON alone.

## Requirements

- Store comparison run DBs under:

```text
data/comparisons/<report-name>/
```

- Use temporary run DB files by default so project-local cleanup is not needed after export.
- Keep cached `source.csv` by default for reproducibility.
- Add:

```text
--keep-run-dbs
```

to preserve run DBs for debugging.

- Include metadata in:

```text
reports/<report-name>_comparison.json
```

Metadata must include:

```text
models
bookmakers
league
season
from_date
to_date
min_history
generated_at
source_path
source_url
keep_run_dbs
```

## Acceptance

Default comparison leaves no scratch DBs under `data/comparisons/<report-name>/`.

With `--keep-run-dbs`, scratch DB files remain under `data/comparisons/<report-name>/`.

## Update

Task 17 changed default scratch DB handling. Default runs now use an OS temporary directory for per-run SQLite files and retain only `source.csv` under `data/comparisons/<report-name>/`. `--keep-run-dbs` keeps per-run SQLite files under the comparison directory.
