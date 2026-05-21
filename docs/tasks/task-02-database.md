# Codex Task 02 — Database Layer

## Goal

Implement SQLite database models and initialization.

## Files

Create/modify:

```text
app/db/engine.py
app/db/models.py
app/db/repositories.py
app/db/migrations.py
app/cli.py
```

## Tables

Implement models for:

```text
matches
odds_snapshots
features
predictions
paper_bets
decision_logs
evaluation_runs
```

Use the schema from `04_DATABASE_SCHEMA.md`.

## CLI

Implement:

```bash
python -m app.cli init-db
```

## Requirements

- Use SQLAlchemy.
- Create DB path from config.
- Ensure `data/` directory exists.
- Add created_at and updated_at helpers.
- Add basic repository methods.
- Enforce unique constraints where specified.

## Acceptance

Running:

```bash
python -m app.cli init-db
```

creates:

```text
data/paper_odds_lab.sqlite
```

and all tables.

## Tests

Add tests for:

```text
DB initialization
match insert
duplicate match handling
odds snapshot insert
decision log insert
```
