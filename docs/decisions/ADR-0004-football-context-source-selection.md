# ADR-0004 - Football Context Source Selection

Date: 2026-06-08

## Status

Accepted

## Context

Misli live recommendations can currently run from public list-page odds, but fresh rows often remain odds-first cold-start candidates. Task 84 needs a permitted, reproducible football context source before changing feature scoring further.

## Decision

Use Football-Data CSV files as the first approved external football context source.

Football-Data is selected because the project already has an importer for its public CSV format, the data can be pinned by local file or deterministic URL, imported rows are stored as normal `matches` and `odds_snapshots`, and completed match history can feed the existing feature builder without adding protected scraping or account automation.

Approved first slice:

- completed match results
- recent form
- rest days
- goal-difference trend
- Elo history from completed matches
- source provenance label `external_context:football_data_csv`
- enriched-versus-local backtest grouping

## Reviewed Sources

Football-Data CSV:

- Fit: accepted first source.
- Notes: public free CSV/Excel football data source with results and odds files; current site notes free football data and at-least-twice-weekly updates.
- Integration: already supported by `FootballDataCsvProvider` and `FootballDataImportService`.

OpenFootball:

- Fit: useful fallback for public-domain historical fixtures/results.
- Notes: public-domain project, but thinner odds/provider context than Football-Data.
- Integration: defer until a JSON provider contract is needed.

football-data.org:

- Fit: possible future official API source for fixtures, standings, and teams.
- Notes: API/token/rate-plan dependency makes it less suitable than CSV for this offline-first task.
- Integration: defer until API credential and rate-limit handling is explicitly planned.

## Boundaries

Do not add:

- bookmaker account automation
- protected scraping
- CAPTCHA or Cloudflare bypass
- stealth browser automation
- proxy evasion
- injury or lineup scraping from unstable pages

## Consequences

Recommendations can now be labelled when their features use external Football-Data CSV context. Backtests can compare external-context recommendations against local-or-unknown recommendations before any Task 83 threshold policy is approved.

The first slice still depends on team-name matching. Team alias management remains future work before this source can reliably enrich every Misli row.
