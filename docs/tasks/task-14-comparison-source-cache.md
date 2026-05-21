# Task 14 - Comparison Source Cache

## Goal

Avoid repeated CSV reads/downloads during replay comparisons by caching the Football-Data source once per comparison run.

## Requirements

- `compare-replays` should create:

```text
data/comparisons/<report-name>/source.csv
```

- If `--path` is provided, copy that file once to `source.csv`.
- If `--url` is provided, download that URL once to `source.csv`.
- If neither is provided, download the Football-Data CSV once from league/season into `source.csv`.
- Every replay run should use the cached `source.csv` path.
- Comparison JSON metadata should include:

```text
cached_source_path
```

- If `--keep-run-dbs` is false, scratch DB files should be temporary and `source.csv` should remain available for reproducibility.

## Acceptance

Comparison runs use one cached source file for all model/bookmaker combinations.

`data/comparisons/<report-name>/source.csv` remains available for audit/debugging.

With `--keep-run-dbs`, per-run SQLite files also remain available.

Task 17 moved default per-run SQLite files into an OS temporary directory. This avoids project-local cleanup issues on Windows. Rerunning the same comparison still clears and recreates the comparison workspace before caching `source.csv`.
