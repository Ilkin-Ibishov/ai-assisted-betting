# Task 10 - Lightweight Schema Migrations

## Goal

Add a small SQLite migration layer so existing local databases can evolve safely as the schema changes.

## Problem

The Elo task added columns to `features`:

```text
home_elo_rating
away_elo_rating
```

Fresh databases work, but older databases created before Elo do not have these columns. `Base.metadata.create_all()` does not alter existing tables.

## Requirements

- Add a `schema_migrations` table.
- Run migrations from `init-db`.
- Make migrations idempotent.
- Add migration:

```text
001_add_feature_elo_columns
```

- The migration should add missing columns only if they are absent.
- Running `init-db` repeatedly must be safe.

## Acceptance

Tests must prove:

- fresh DB initialization still creates all tables
- an old DB missing Elo columns is upgraded
- running migrations twice does not fail or duplicate records

## Out Of Scope

- Full Alembic setup.
- Downgrade migrations.
- Cross-database migration support beyond SQLite MVP.

