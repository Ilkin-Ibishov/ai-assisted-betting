# Task 18 - Comparison Parallel Execution

## Goal

Run replay comparison model/bookmaker combinations concurrently while preserving deterministic report order and isolated run databases.

## Problem

`compare-replays` previously ran every model/bookmaker combination sequentially. This was simple, but slow as comparison grids grew.

## Requirements

- Run independent model/bookmaker jobs through a bounded worker pool.
- Preserve the original report ordering:

```text
models order, then bookmakers order
```

- Keep one isolated SQLite database per model/bookmaker combination.
- Continue using temporary run databases by default and retained run databases with `--keep-run-dbs`.
- Include `parallel_workers` in comparison JSON metadata.
- Keep ranking, CSV, and JSON outputs deterministic.

## Acceptance

Comparison service tests prove multiple model/bookmaker jobs can overlap.

CLI comparison reports still include all existing fields, rankings, and workspace metadata.

## Implementation Notes

Implemented in `app/services/comparison_service.py`.

What was done:

- Added bounded parallel comparison execution with `ThreadPoolExecutor`.
- Extracted per-run comparison work into a single job helper.
- Kept result order deterministic by using ordered executor mapping.
- Added `parallel_workers` metadata to comparison JSON.
- Added a unit test that proves model/bookmaker jobs overlap.

What's next:

- Task 20 made the worker count configurable through `compare-replays --workers`.

Blockers:

- None.

Technical debt:

- The sequential comparison debt is resolved.
- The fixed worker-count debt is resolved by Task 20.
