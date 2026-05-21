# Task 54 - Live Odds Movement Tracking

## Goal

Track how Misli odds change over time so recommendations can use movement, freshness, and market stability signals.

## Requirements

- Store odds snapshots per provider event, market, outcome, and collection timestamp.
- Preserve the best current price, previous price, opening observed price, and movement direction.
- Expose movement summaries through the API and dashboard data layer.
- Mark stale odds and suspended/missing outcomes explicitly.
- Keep the model paper-only and do not infer bet placement status from bookmaker UI.

## Acceptance Criteria

- Completed: repeated snapshots for the same event produce an auditable odds timeline through existing `odds_snapshots` rows.
- Completed: the system can answer whether an outcome moved up, moved down, stayed stable, disappeared, or became stale.
- Completed: dashboard/API consumers can show current odds plus recent movement through `GET /api/live/odds-movement` and `fetchOddsMovement()`.
- Completed: tests cover repeated snapshots, missing outcomes, stale movement windows, and API/frontend data-layer access.

## Implementation Notes

- Added `app/services/odds_movement_service.py`.
- Added read-only endpoint:

```text
GET /api/live/odds-movement
```

- Added dashboard API data type/helper:

```text
dashboard/src/lib/api.ts -> fetchOddsMovement()
```

- Movement is computed from `odds_snapshots`, grouped by match, bookmaker, market, and selection.
- Status values: `active`, `missing`, `stale`.
- Movement values: `new`, `up`, `down`, `stable`, `missing`, `stale`.

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

Task 55 - Paper Bet Recommendation Engine.

## Blockers

None for the completed movement summary layer.

## Technical Debt

Accepted tradeoff: odds movement is computed from existing `odds_snapshots` instead of a dedicated movement table. This avoids duplicated state for MVP. If queries become slow after deployed collection, add a materialized summary table or cached view during monitoring/backtesting work.
