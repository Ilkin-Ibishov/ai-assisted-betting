# Task 12 - Replay Comparison Command

## Goal

Add a command that runs multiple replay experiments over the same dataset/window and exports a side-by-side comparison summary.

## CLI

Add:

```powershell
python -m app.cli compare-replays
```

Options:

```text
--league
--season
--path
--url
--models baseline_heuristic,elo
--bookmakers B365,Avg
--from-date
--to-date
--min-history
--report-name
```

## Requirements

- Run one isolated replay per model/bookmaker combination.
- Use separate scratch SQLite DB files per combination under `data/comparisons/<report-name>/`.
- Cache the source CSV once per comparison as `data/comparisons/<report-name>/source.csv`.
- Delete scratch DBs by default unless `--keep-run-dbs` is set.
- Export a comparison CSV and JSON summary:

```text
reports/<report-name>_comparison.csv
reports/<report-name>_comparison.json
```

- Include at least:

```text
model
bookmaker
total_bets
settled_bets
wins
losses
roi
profit_loss_units
average_odds
average_edge
brier_score
log_loss
```

## Acceptance

Example:

```powershell
python -m app.cli compare-replays --league E0 --season 2526 --models baseline_heuristic,elo --bookmakers B365,Avg --report-name e0_compare
```

creates comparison artifacts and prints a compact table.

Comparison JSON should include rankings for best ROI, best Brier score, and best log loss. Comparison CSV should include rank columns for those metrics.
