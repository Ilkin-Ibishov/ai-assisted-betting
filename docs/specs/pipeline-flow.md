# 06 — Pipeline Flow

## Main Commands

The CLI must expose:

```bash
python -m app.cli init-db
python -m app.cli import-sample-data
python -m app.cli collect-matches
python -m app.cli collect-odds
python -m app.cli generate-features
python -m app.cli generate-predictions
python -m app.cli write-paper-bets
python -m app.cli settle-results
python -m app.cli evaluate
```

## MVP Local Flow

### Step 1 — Init DB

```bash
python -m app.cli init-db
```

Creates SQLite DB and tables.

### Step 2 — Import Sample Data

```bash
python -m app.cli import-sample-data
```

Adds sample scheduled/completed matches and odds.

### Step 3 — Generate Features

```bash
python -m app.cli generate-features
```

Creates features for eligible matches.

### Step 4 — Generate Predictions

```bash
python -m app.cli generate-predictions
```

Runs prediction engine.

Use `--model` to override `MODEL_NAME` for this command:

```bash
python -m app.cli generate-predictions --model elo
```

### Step 5 — Write Paper Bets

```bash
python -m app.cli write-paper-bets
```

Writes paper bets for predictions with decision = BET.

Use `--model` to select which model's predictions are evaluated for paper bets:

```bash
python -m app.cli write-paper-bets --model elo
```

### Step 6 — Settle Results

```bash
python -m app.cli settle-results
```

Settles open paper bets where match result is known.

### Step 7 — Evaluate

```bash
python -m app.cli evaluate
```

Prints metrics and writes evaluation run.

## Live Paper Betting Flow

```text
1. collect-matches
2. collect-odds
3. generate-features
4. generate-predictions
5. write-paper-bets
6. later: settle-results
7. evaluate
```

The detailed next-phase plan lives in:

```text
docs/specs/live-paper-loop.md
```

Build it through Tasks 38-45 before adding scheduling or real-money execution.

## Replay / Historical Flow

```text
HistoricalProvider
    ↓
same Normalizer
    ↓
same DB
    ↓
same FeatureBuilder
    ↓
same PredictionEngine
    ↓
same ValueDetector
    ↓
same PaperBetLogger
    ↓
same Evaluator
```

## Replay Comparison Workspace

`compare-replays` should cache the source CSV at:

```text
data/comparisons/<report-name>/source.csv
```

Default comparison runs should use temporary per-run SQLite databases and leave no `.sqlite` files in the comparison workspace after export.

When `--keep-run-dbs` is used, per-run SQLite files should remain under:

```text
data/comparisons/<report-name>/
```

Independent model/bookmaker comparison jobs may run in parallel. Report rows should remain deterministic in model order, then bookmaker order. Use `--workers` to tune the parallel worker count. Comparison JSON metadata should record the actual number of `parallel_workers` used.

## Idempotency Rules

Commands must be safe to run multiple times.

Examples:

- Do not duplicate matches with same `(source, source_match_id)`.
- Do not duplicate feature rows with same `(match_id, market, selection, feature_version)`.
- Do not create duplicate paper bets for same prediction.
- Odds snapshots may duplicate only if snapshot time/source/market/selection differ.

## Error Handling

Each command must:

1. Validate input.
2. Log failures.
3. Continue when safe.
4. Never crash the entire pipeline due to one bad match.
5. Return non-zero exit only on systemic failure.

## Minimum CLI Output

Each command should print:

```text
started
items_read
items_created
items_updated
items_skipped
errors_count
finished
```
