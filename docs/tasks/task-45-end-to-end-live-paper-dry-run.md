# Task 45 - End-To-End Live Paper Dry Run

## Goal

Prove the live paper workflow works end to end with a permitted provider or deterministic fake/manual provider.

## Requirements

- Run the live paper cycle from collection through paper bet writing.
- Collect or load results.
- Settle paper bets.
- Evaluate results.
- Verify dashboard process status.
- Document exact command sequence.
- Prefer a Misli public snapshot dry run if Tasks 38 and 40 validate full kickoff datetimes.
- Fall back to deterministic fake/manual provider if Misli validation remains incomplete.

## Acceptance Criteria

The dry run must prove:

```text
implemented: no duplicate matches on repeated cycle
implemented: no duplicate paper bets on repeated cycle
implemented: run registry captures collection, odds, cycle, and result stages
implemented: errors are visible for the current real Misli public snapshot
implemented: dashboard process monitor renders the dry-run status
implemented: Misli public snapshot path is explicitly skipped with documented validation reason
implemented: full verification passes
```

## Implementation Notes

Task 45 added deterministic fixture files:

```text
docs/fixtures/task45-live-dry-run-snapshot.json
docs/fixtures/task45-live-dry-run-results.json
```

The fixture uses `misli_public` DTO shape with a complete kickoff datetime and complete 1X2 odds. It is not scraped live data. It exists only to prove the local paper-only workflow while the real Misli public snapshot still lacks full kickoff dates.

## Dry Run Database

The dry run used an isolated SQLite database:

```powershell
$env:DATABASE_URL='sqlite:///data/task45-live-dry-run.sqlite'
$env:MIN_EDGE='0.01'
$env:MODEL_NAME='baseline_heuristic'
$env:MODEL_VERSION='v0'
```

`MIN_EDGE=0.01` was used so the deterministic fixture creates at least one paper bet with the current baseline model. This is a dry-run proof setting, not a production staking recommendation.

## Command Transcript

Real Misli public snapshot was refreshed with:

```powershell
node tools\misli-public-snapshot.mjs --out data\misli-public-snapshot.task45.json
```

Snapshot validation summary:

```text
event_count=21
missing_kickoff_date=21
```

The real Misli path failed closed as expected:

```powershell
python -m app.cli init-db
python -m app.cli collect-matches --provider misli-public --snapshot data\misli-public-snapshot.task45.json --league football --season task45-real-misli
python -m app.cli collect-odds --provider misli-public --snapshot data\misli-public-snapshot.task45.json --league football --season task45-real-misli
```

Observed:

```text
collect-matches: items_read=21, items_created=0, items_skipped=21, errors_count=21
collect-odds: items_read=21, items_created=0, items_skipped=21, errors_count=21
reason: Misli event requires a full kickoff date and time
```

The deterministic successful dry run used:

```powershell
python -m app.cli import-sample-data
python -m app.cli collect-matches --provider misli-public --snapshot docs\fixtures\task45-live-dry-run-snapshot.json --league task45-fixture --season 2026
python -m app.cli collect-odds --provider misli-public --snapshot docs\fixtures\task45-live-dry-run-snapshot.json --league task45-fixture --season 2026
python -m app.cli run-live-paper-cycle --provider misli-public --snapshot docs\fixtures\task45-live-dry-run-snapshot.json --model baseline_heuristic --league task45-fixture --season 2026
python -m app.cli run-live-paper-cycle --provider misli-public --snapshot docs\fixtures\task45-live-dry-run-snapshot.json --model baseline_heuristic --league task45-fixture --season 2026
python -m app.cli collect-results --provider manual --path docs\fixtures\task45-live-dry-run-results.json --league task45-fixture --season 2026
python -m app.cli settle-results
python -m app.cli evaluate
```

First cycle observed:

```text
status=completed
collect_matches: items_created=0, items_skipped=1
collect_odds: items_created=0, items_skipped=3
generate_features: items_created=6, items_skipped=6
generate_predictions: items_created=6
write_paper_bets: items_created=2, items_skipped=4
```

Repeated cycle observed:

```text
status=completed
items_created=0
write_paper_bets.items_created=0
```

Result and settlement observed:

```text
collect-results: items_read=1, items_updated=1, errors_count=0
settle-results: items_read=2, items_updated=1, items_skipped=1, errors_count=0
evaluate: total_bets=2, settled_bets=1, wins=1, ROI=1.1
```

Database summary:

```text
matches=12
odds_snapshots=12
predictions=6
paper_bets=2
live_runs=6
task45 match status=completed 2-1 HOME
task45 odds=3
task45 predictions=3
task45 paper_bets=1
task45 paper_bet_statuses=[won: 1]
```

Dashboard monitor observed:

```text
latest_run=collect_results completed
open_paper_bets=1
settled_paper_bets=1
runs_count=6
errors_count=42
latest_failure=collect_odds real Misli snapshot
```

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

Also record the manual command transcript in this task doc or a linked runbook.

## Next

After Task 45, decide whether to:

```text
promote Misli public snapshot from prototype to maintained provider adapter
resolve live cycle run scoping before scheduling
add scheduling
improve prediction models
expand markets beyond 1X2
```

## Blockers

Misli-specific blocker: public 1X2 odds are available, but the end-to-end Misli dry run depends on reliable full kickoff datetime handling.

## Technical Debt

The deterministic fixture proves the engine path but does not make real Misli import ready. Real Misli remains blocked by kickoff date extraction.

The repeated cycle proves duplicate protection, but `run-live-paper-cycle` still processes all scheduled matches in the active database. This is already tracked as P3 technical debt and should be resolved before scheduling or multi-provider operation.
