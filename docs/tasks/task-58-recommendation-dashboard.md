# Task 58 - Recommendation Dashboard

## Goal

Add dashboard views for live paper recommendations, combinations, AI review, odds movement, and risk flags.

## Requirements

- Add a recommendations view with ranked singles and combinations.
- Show current odds, movement, edge, confidence, risk flags, provider health, and AI review status.
- Support filtering by grade, market, league, provider health, confidence, and AI approval state.
- Keep dense analytical layout using the existing React/shadcn style.
- Make the view usable on desktop and mobile without overlapping controls or unreadable tables.

## Acceptance Criteria

- Dashboard can inspect a live cycle from collection through recommendation and AI review.
- Users can identify why a candidate was recommended or rejected.
- Mobile smoke screenshots remain readable.
- Tests cover recommendation formatting, filters, risk badge mapping, and API fallbacks.

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

Task 59 - Historical Recommendation Backtesting.

## Blockers

Requires Task 55 recommendation data contract and Task 56 combination data contract.

## Technical Debt

Record any dashboard performance bottlenecks once recommendation history grows.
