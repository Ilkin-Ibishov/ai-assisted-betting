# Task 06 - Football-Data Multi-Bookmaker Odds

## Goal

Extend the Football-Data CSV provider so replay and imports can use multiple 1X2 bookmaker columns, not only Bet365.

## Scope

Support these Football-Data 1X2 column groups when present:

```text
B365H/B365D/B365A
BWH/BWD/BWA
IWH/IWD/IWA
PSH/PSD/PSA
WHH/WHD/WHA
VCH/VCD/VCA
MaxH/MaxD/MaxA
AvgH/AvgD/AvgA
```

## Requirements

- Keep default behavior compatible with the existing `B365` import.
- Add a `--bookmaker` CLI option for `import-football-data` and `replay-football-data`.
- Use `ALL` to import every supported bookmaker present in the CSV.
- Store the selected bookmaker name in `odds_snapshots.bookmaker`.
- Skip missing or blank odds columns without failing the whole import.
- Preserve idempotency across repeated imports.
- Do not add live scraping or browser automation in this task.

## Acceptance

The following should work:

```powershell
python -m app.cli import-football-data --league E0 --season 2526 --bookmaker ALL
python -m app.cli replay-football-data --league E0 --season 2526 --bookmaker Avg
```

## Tests

Add tests for:

```text
provider imports multiple bookmaker groups
provider filters to a selected bookmaker
CLI import is idempotent with ALL
replay accepts bookmaker option
```

