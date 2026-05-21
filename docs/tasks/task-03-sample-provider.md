# Codex Task 03 — Sample Provider and Import

## Goal

Implement deterministic local sample data import.

## Files

Create/modify:

```text
app/providers/base.py
app/providers/sample_provider.py
app/schemas/match.py
app/schemas/odds.py
app/schemas/result.py
app/normalizers/match_normalizer.py
app/normalizers/odds_normalizer.py
app/services/collection_service.py
app/cli.py
```

## Sample Data

Create at least:

```text
8 completed historical matches
3 upcoming/scheduled matches
1X2 odds for each upcoming match
results for completed matches
```

Use fictional teams.

## Requirements

- No network calls.
- Raw provider data must pass through normalizers.
- Store raw payload JSON.
- Write decision logs.

## CLI

Implement:

```bash
python -m app.cli import-sample-data
```

## Acceptance

After:

```bash
python -m app.cli init-db
python -m app.cli import-sample-data
```

DB contains:

```text
matches
odds_snapshots
decision_logs
```

## Tests

Add integration test:

```text
init DB -> import sample data -> verify row counts
```
