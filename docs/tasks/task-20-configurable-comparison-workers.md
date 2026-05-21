# Task 20 - Configurable Comparison Workers

## Goal

Let comparison users tune parallel replay worker count from the CLI.

## Problem

Task 18 added parallel comparison execution with an internal worker cap of 4. That is a safe default, but larger or constrained workloads may need explicit tuning.

## Requirements

- `compare-replays` should accept:

```text
--workers N
```

- `N` must be at least 1.
- Omitted `--workers` should keep the default cap of 4.
- Worker count should still never exceed the number of comparison jobs.
- Comparison JSON should continue to record the actual `parallel_workers` used.

## Acceptance

`compare-replays --workers 2` records `parallel_workers: 2` for a four-run comparison.

`compare-replays --workers 0` fails with a clear validation message.

## Implementation Notes

Implemented in `app/cli.py` and `app/services/comparison_service.py`.

What was done:

- Added `workers` to `ReplayComparisonRequest`.
- Added `--workers` to `compare-replays`.
- Added CLI and service-level validation for worker counts below 1.
- Updated worker-count selection to respect explicit limits and cap at the job count.
- Added integration and unit tests for worker configuration.

What's next:

- Plan the next product phase now that the documented technical debt register has no open items.

Blockers:

- None.

Technical debt:

- The fixed-worker-count debt is resolved.
