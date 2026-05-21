# ADR-0002: SQLite For MVP Storage

## Status

Accepted

## Context

The MVP is local, CLI-first, and focused on proving the data and evaluation pipeline.

## Decision

Use SQLite at `data/paper_odds_lab.sqlite` for the first milestone.

## Consequences

- Local setup stays simple.
- Integration tests can create isolated temporary databases.
- PostgreSQL can be considered later if live collection or multi-user access requires it.

