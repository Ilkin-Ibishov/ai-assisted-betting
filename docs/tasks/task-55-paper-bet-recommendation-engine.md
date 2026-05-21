# Task 55 - Paper Bet Recommendation Engine

## Goal

Generate ranked paper-only bet recommendations from live Misli events using deterministic model signals before any AI review.

## Requirements

- Combine prediction probability, bookmaker odds, implied probability, expected value, calibration, freshness, and provider health.
- Assign recommendation grades such as watch, lean, recommended, and reject.
- Include rejection reasons for weak or unsafe candidates.
- Persist recommendations with model version, prompt-free rationale fields, source run ID, and input snapshot references.
- Expose recommendations through CLI and API.
- Never place bets or produce instructions to interact with bookmaker accounts.

## Acceptance Criteria

- Completed: a live database can produce zero or more ranked recommendations from collected odds and predictions.
- Completed: every persisted recommendation includes probability, implied probability, edge, confidence, current odds, expected value, risk flags, and deterministic rationale.
- Completed: low-quality candidates are rejected rather than silently omitted.
- Completed: tests cover positive-edge, negative-edge, stale-data, unhealthy-provider, and low-confidence scenarios.

## Implementation Notes

- Added `paper_recommendations` persistence through SQLAlchemy model and SQLite migration `005_create_paper_recommendations`.
- Added `app/services/recommendation_service.py`.
- Added CLI command:

```powershell
python -m app.cli generate-recommendations --stale-after-minutes 60
```

- Added read-only API endpoint:

```text
GET /api/live/recommendations
```

- Grades: `recommended`, `lean`, `watch`, `reject`.
- Recommendation scoring is deterministic and paper-only. It does not create `paper_bets`, place bets, or automate bookmaker interactions.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
cd dashboard
npm run test
npm run lint
npm run build
npm run smoke
```

## Next

Task 56 - Paper Bet Combination Engine.

## Blockers

None for the completed deterministic recommendation engine.

## Technical Debt

Accepted technical debt: recommendation expected value uses fixed unit-stake arithmetic and does not yet include bankroll sizing, exposure caps, correlation, or drawdown controls. Task 56 should add combination/exposure rules, and later backtesting should validate thresholds.
