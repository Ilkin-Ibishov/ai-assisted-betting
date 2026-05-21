# ADR-0001: Offline First MVP

## Status

Accepted

## Context

The project needs auditable betting research behavior before any live data source is introduced. Live collection can create legal, reliability, and data quality risks if added too early.

## Decision

Build a deterministic offline sample pipeline first. The MVP must run without network access and must use fake paper bets only.

## Consequences

- SampleProvider is mandatory.
- Tests must use local fixtures.
- Live API providers are deferred until the offline engine is stable.

