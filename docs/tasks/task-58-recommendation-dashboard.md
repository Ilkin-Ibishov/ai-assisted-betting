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

## Implementation Notes

Completed in Task 58:

- Added a read-only Recommendation Dashboard panel to the existing React workspace.
- Added parallel frontend data loading for live recommendations, combinations, odds movement, and latest AI recommendation review.
- Added typed API helpers for `GET /api/live/recommendations` and `GET /api/ai/recommendation-review/latest`.
- Added dashboard filtering by grade, market, confidence band, and AI approval state.
- Added recommendation rows with match label, selection, market, current odds, odds movement, edge, confidence, grade, and risk badges.
- Added ranked paper-combination cards with leg count, rank, combined EV, odds, grade, and risk flags.
- Added AI review summary, approval state, and next-check display.
- Added tested recommendation dashboard helper logic for formatting, filters, risk-badge tones, API fallback behavior, and recommendation-to-odds movement joining.
- Extended Playwright smoke coverage to assert the recommendation dashboard on desktop and mobile.

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

The first dashboard view renders the API-limited recommendation set directly without virtualization. Track performance once recommendation history grows beyond the current API limits.
