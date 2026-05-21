# Task 07 - Replay Filters And Report Export

## Goal

Make historical replay runs reproducible and inspectable by adding replay filters and report exports.

## CLI

Extend:

```powershell
python -m app.cli replay-football-data
```

with:

```text
--from-date YYYY-MM-DD
--to-date YYYY-MM-DD
--min-history INTEGER
--report-name NAME
```

## Requirements

- `from-date` filters replay candidate matches by kickoff date, inclusive.
- `to-date` filters replay candidate matches by kickoff date, inclusive.
- `min-history` controls the minimum prior completed matches required per team.
- `report-name` writes:

```text
reports/<report-name>_bets.csv
reports/<report-name>_summary.json
```

- Report export must include settled/open paper bets with match, prediction, odds, status, and P/L details.
- Summary JSON must match the evaluation report stored in the database.

## Acceptance

Example:

```powershell
python -m app.cli replay-football-data `
  --league E0 `
  --season 2526 `
  --bookmaker Avg `
  --from-date 2025-08-01 `
  --to-date 2025-12-31 `
  --min-history 5 `
  --report-name e0_avg_aug_dec
```

creates:

```text
reports/e0_avg_aug_dec_bets.csv
reports/e0_avg_aug_dec_summary.json
```

