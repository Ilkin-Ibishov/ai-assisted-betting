# Task 74 - Richer Team Strength Feature Inputs

Status: completed

## Goal

Improve recommendation quality by adding real team and match context beyond odds-first cold-start features.

## Requirements

- Add vetted football context fields that can be computed or collected reliably.
- Prioritize:
  - recent home and away split
  - opponent-adjusted form
  - league strength or table position
  - rest days
  - goal difference trend
  - odds movement velocity
  - market overround normalization
  - closing-line movement tracking
- Keep missing context fail-soft: recommendations should remain auditable and conservative when data is incomplete.
- Record feature provenance so AI review can distinguish odds-only rows from enriched rows.

## Acceptance Criteria

- Feature rows expose whether they are cold-start, partially enriched, or fully enriched.
- Prediction outputs change only when the richer feature signals are present.
- AI review can flag odds-only actionable rows separately from enriched actionable rows.
- Tests cover missing data, partial data, and enriched data paths.

## Implementation Notes

- Prefer deterministic public/statistical data sources already compatible with the paper-only design.
- Avoid protected scraping or sources that require bookmaker account automation.
- Add source contracts before wiring data into scoring.
- Keep features explainable; avoid black-box ML until the data pipeline is reliable.

## Implementation Summary

- Added feature enrichment columns for `enrichment_tier`, `feature_provenance_json`, rest days, goal-difference trend, and odds movement velocity.
- Feature rows now classify as `cold_start`, `partial_enriched`, or `full_enriched`.
- Feature provenance records deterministic local inputs such as market overround normalization, recent form, rest days, goal-difference trend, odds movement velocity, and Elo ratings when available.
- Baseline prediction behavior remains unchanged for `cold_start` rows.
- Baseline prediction output shifts only when `partial_enriched` or `full_enriched` feature signals are present.
- Prediction reasons preserve `feature_tier` and `feature_provenance` through value detection.
- AI recommendation review now counts odds-only actionable recommendations separately from enriched actionable recommendations and flags odds-only actionable rows.
- External source selection remains intentionally deferred; this slice uses only already-owned match and odds data.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_core_engine.py tests/unit/test_recommendation_service.py tests/unit/test_ai_analysis_service.py
.\.venv\Scripts\python.exe -m ruff check app tests
```

Verified on 2026-06-04:

- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_core_engine.py tests/unit/test_recommendation_service.py tests/unit/test_ai_analysis_service.py -q` - 33 passed.
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_database.py -q` - 18 passed.
- `.\.venv\Scripts\python.exe -m ruff check app tests` - passed.

## Next

Task 75 - Daily Paper Trading Journal.

## Blockers

External source selection remains open. Candidate sources should be reviewed for stability, legality, and reproducibility before adding league table, opponent-adjusted, lineup, injury, or closing-line data beyond the existing local paper loop.

## Technical Debt

Cold-start rows are now explicitly labeled and fail soft, but they can still produce recommendations when market/EV signals are strong. AI review flags those rows so later backtests and journal entries can decide whether to tighten or quarantine them.
