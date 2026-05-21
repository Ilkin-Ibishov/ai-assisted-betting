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

- Repeated snapshots for the same event produce an auditable odds timeline.
- The system can answer whether an outcome moved up, moved down, stayed stable, disappeared, or became stale.
- Dashboard/API consumers can show current odds plus recent movement.
- Tests cover duplicate snapshot ingestion, missing outcomes, and stale movement windows.

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

Requires Task 53 hardened normalized Misli collection.

## Technical Debt

If odds history is initially stored in existing tables instead of a dedicated table, record the schema tradeoff and migration path.
