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

Document correlation rules that are heuristic and need historical validation.
