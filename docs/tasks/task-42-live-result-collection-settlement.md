# Task 42 - Live Result Collection And Settlement Flow

## Goal

Collect completed match results and settle open paper bets in a live-paper workflow.

## Requirements

- Implement or complete `collect-results`.
- Normalize provider result payloads.
- Reuse existing settlement behavior.
- Record run registry entries.
- Keep settlement idempotent.

## Command Direction

```powershell
python -m app.cli collect-results --provider <provider> --league <league>
python -m app.cli settle-results
```

## Acceptance Criteria

- Results update completed matches without duplicating data.
- Open paper bets settle when results become available.
- Re-running settlement is safe.
- Registry exposes result collection status.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

## Implementation Status

Completed in code:

```text
app/services/live_result_service.py
app/cli.py
tests/unit/test_live_result_service.py
tests/integration/test_cli.py
```

Implemented:

```text
collect-results --provider manual --path <results.json>
manual result JSON loading
match result updates by source + source_match_id
idempotent completed-match handling
missing-match errors recorded in live_runs
settle-results reuse after result collection
settlement rerun safety
```

Manual result JSON shape:

```json
{
  "source": "manual",
  "collected_at": "2026-05-20T01:00:00+04:00",
  "results": [
    {
      "source": "misli_public",
      "source_match_id": "misli:football:2816300",
      "home_score": 2,
      "away_score": 1,
      "result": "HOME"
    }
  ]
}
```

## Next

Task 43 - Live Process Status API.

## Blockers

None for Task 43. Provider-native result collection remains out of scope.

## Technical Debt

Manual result JSON is the only implemented result provider. Provider-native public result discovery is still future work.
