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

- A live cycle can produce zero or more ranked recommendations from collected events.
- Every recommendation includes probability, implied probability, edge, confidence, risk flags, and plain-language deterministic rationale.
- Low-quality candidates are rejected rather than silently omitted.
- Tests cover positive-edge, negative-edge, stale-data, unhealthy-provider, and low-confidence scenarios.

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

Requires Task 54 odds movement tracking and stable live recommendation inputs.

## Technical Debt

Document any simplified bankroll or staking assumptions until a richer risk model exists.
