# Task 84 - External Football Context Source Selection

Status: completed

## Goal

Select and integrate vetted football context sources so Misli recommendations are not mostly odds-first cold-start guesses.

Task 74 added local enrichment fields and provenance. This task should choose safe, reproducible public or official sources for richer team and match context, then wire the first approved slice into the existing feature pipeline.

## Requirements

- Evaluate candidate sources for legality, stability, freshness, coverage, cost, and reproducibility.
- Prefer official APIs, licensed datasets, public CSVs, or user-provided files.
- Do not use protected scraping, bookmaker account automation, CAPTCHA bypass, Cloudflare bypass, stealth automation, or proxy evasion.
- Define provider contracts before feature scoring changes.
- Capture raw payloads and provenance for every imported context record.
- Add at least one approved context source for team strength or schedule context.
- Feed the approved source into feature enrichment without breaking cold-start fail-soft behavior.
- Make AI review distinguish externally enriched recommendations from local-only recommendations.
- Backtest enriched versus local-only recommendation quality before changing primary thresholds.

## Candidate Context Areas

- League table position and points-per-match.
- Opponent-adjusted recent form.
- Home/away split.
- Rest days and schedule congestion.
- Injuries and lineup availability, only if sourced from a permitted and stable provider.
- Closing-line movement, only if sourced from allowed historical odds data.

## Acceptance Criteria

- A source-selection note records why the chosen source is allowed and reproducible.
- Imported context rows are idempotent and traceable to source ids.
- Feature provenance shows the external context source.
- Prediction/recommendation behavior changes only when the new context exists.
- Backtest output compares local-only versus externally enriched candidates.
- Dashboard or AI review clearly labels enriched recommendations.

## Source Selection

Selected source: Football-Data CSV.

Decision note:

```text
docs/decisions/ADR-0004-football-context-source-selection.md
```

Football-Data CSV is the first approved source because it is public CSV/Excel data, already supported by the existing importer, reproducible by local file or pinned URL, and compatible with the offline-first architecture. It does not require bookmaker account automation, protected scraping, bot bypass, or live browser sessions.

Reviewed but deferred:

- OpenFootball public-domain datasets: useful fallback, but thinner for the current odds/recommendation context.
- football-data.org API: useful future official API path, but introduces API token/rate-plan handling that is not needed for the first Task 84 slice.

## Implementation Notes

- Feature provenance now adds `external_context:football_data_csv` when scheduled match features are built from completed Football-Data history.
- AI recommendation review now counts `external_context_actionable_count` and flags `external_context_recommendations_present` so enriched rows remain visible but provisional.
- Recommendation backtests now include `source_context_buckets` with `external_context` versus `local_or_unknown` metrics.
- Existing cold-start fail-soft behavior is preserved. Predictions only change when the existing enrichment fields are populated from matching historical context.
- No real-money betting, protected scraping, account automation, CAPTCHA bypass, Cloudflare bypass, stealth automation, or proxy evasion was added.

## Verification

Fresh verification must pass before final handoff:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
cd dashboard
npm run test
npm run lint
npm run build
```

## Suggested Verification

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
cd dashboard
npm run test
npm run lint
npm run build
```

## Next

Use enriched backtest evidence to decide whether Task 83 threshold policy should approve any strategy changes.

## Blockers

No current implementation blocker. Team-name aliases remain a coverage limitation for Misli rows whose names do not exactly match Football-Data team names.

## Technical Debt

The current system can now label Football-Data CSV external context and compare it in backtests. Remaining debt is coverage: team aliases and broader context sources are still needed before daily decision support can be considered mature.
