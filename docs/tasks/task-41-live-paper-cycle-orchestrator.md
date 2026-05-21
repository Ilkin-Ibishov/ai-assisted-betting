# Task 41 - Live Paper Cycle Orchestrator

## Goal

Add one safe command that runs the paper-only live prediction and bet-writing cycle.

## Requirements

- Orchestrate collection, features, predictions, and paper bet writing.
- Record one live run registry entry for the cycle.
- Respect duplicate protection.
- Support model selection.
- Keep settlement out of this command initially.

## Command Direction

```powershell
python -m app.cli run-live-paper-cycle --provider <provider> --league <league> --model elo
```

## Acceptance Criteria

- Command can be rerun without duplicate paper bets.
- Command reports counters for each stage.
- Failures in one match do not stop unrelated matches when safe.
- Registry captures status and errors.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

## Implementation Status

Completed in code:

```text
app/services/live_cycle_service.py
app/cli.py
tests/unit/test_live_cycle_service.py
tests/integration/test_cli.py
```

Implemented:

```text
run-live-paper-cycle --provider <provider> --snapshot <path> --model <model>
cycle-level live_runs entry
stage summaries for collect_matches, collect_odds, generate_features, generate_predictions, write_paper_bets
idempotent rerun without duplicate paper bets
failed cycle status when collection validation fails
settlement remains out of scope
```

## Next

Task 42 - Live Result Collection And Settlement Flow.

## Blockers

None for Task 42. Misli real-data import still depends on full kickoff datetime extraction.

## Technical Debt

The cycle reuses the existing broad prediction service methods, so it can process any currently scheduled match in the database, not only matches collected by the current live snapshot. This is acceptable for MVP but should be revisited if live and replay data need stricter isolation.
