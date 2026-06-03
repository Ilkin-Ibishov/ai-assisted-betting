# Task 74 - Richer Team Strength Feature Inputs

Status: planned

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

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_core_engine.py tests/unit/test_recommendation_service.py tests/unit/test_ai_analysis_service.py
.\.venv\Scripts\python.exe -m ruff check app tests
```

## Next

Task 75 - Daily Paper Trading Journal.

## Blockers

Source selection must be decided before implementation. Candidate sources should be reviewed for stability, legality, and reproducibility.

## Technical Debt

Current live features can still be odds-first and neutral for teams without completed-match history. That keeps the pipeline alive but limits prediction intelligence.
