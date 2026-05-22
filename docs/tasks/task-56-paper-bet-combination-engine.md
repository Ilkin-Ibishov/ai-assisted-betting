# Task 56 - Paper Bet Combination Engine

## Goal

Build paper-only bet-combination suggestions that avoid naive high-odds parlays and account for correlation, confidence, and exposure.

## Requirements

- Combine only recommendations that passed deterministic filters.
- Reject combinations with duplicate event exposure, correlated outcomes, stale odds, unhealthy provider state, or excessive combined risk.
- Calculate combined odds, estimated probability, expected value, confidence score, and risk flags.
- Support configurable maximum legs, minimum leg confidence, and maximum combined-risk thresholds.
- Persist combination suggestions and expose them through CLI/API.

## Acceptance Criteria

- The system can generate single-leg and multi-leg recommendation sets.
- Combination ranking favors disciplined expected value and confidence, not only combined odds.
- Tests cover duplicate-event rejection, correlated-market rejection, stale-leg rejection, and maximum-leg enforcement.
- Dashboard can consume combination data without additional backend transformation.

## Implementation Notes

Completed in Task 56:

- Added `paper_combinations` storage with migration `006_create_paper_combinations`.
- Added `CombinationService` to generate ranked single-leg and multi-leg paper combinations from active deterministic recommendations.
- Added duplicate event exposure rejection, stale/provider-risk leg filtering, maximum-leg enforcement, `max_risk_flags` enforcement, EV/probability/confidence scoring, and risk flags.
- Added `generate-combinations` CLI command with `--max-legs`, `--min-leg-confidence`, `--max-risk-flags`, and `--max-combinations`.
- Added `GET /api/live/combinations` and typed dashboard API helper `fetchPaperCombinations`.
- Added unit/API/CLI coverage for service behavior, migration records, API payloads, and CLI persistence.

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

Task 57 - AI Recommendation Review Layer.

## Blockers

Requires Task 55 recommendation engine.

## Technical Debt

Combination correlation and exposure rules are heuristic and need historical validation in Task 59 before they should influence any serious paper strategy decisions.
