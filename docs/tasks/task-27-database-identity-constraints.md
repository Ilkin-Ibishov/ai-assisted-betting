# Task 27 - Database Identity Constraints

## Goal

Make the documented idempotency and uniqueness rules explicit for existing SQLite databases.

## Requirements

- Ensure old databases receive a unique identity index for `odds_snapshots`.
- Ensure old databases receive a unique index for `paper_bets.prediction_id`.
- Keep existing ORM constraints for newly created databases.
- Update schema and agent-context docs.

## Implementation

Status: completed

Added migration:

```text
002_add_identity_unique_indexes
```

Migration behavior:

```text
CREATE UNIQUE INDEX IF NOT EXISTS uq_odds_snapshot_identity
ON odds_snapshots(match_id, source, bookmaker, market, selection, snapshot_time)

CREATE UNIQUE INDEX IF NOT EXISTS uq_paper_bets_prediction_id
ON paper_bets(prediction_id)
```

Added database test coverage proving an old SQLite database receives both unique indexes and records the migration.

## Verification

Passed:

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

Choose the next product phase. Reasonable candidates:

```text
dashboard report catalog / comparison history
replay-analysis improvements
data-ingestion/provider robustness
```

## Notes

If an old database already contains duplicate rows for either identity rule, SQLite will reject the unique index creation. That is intentional: duplicates should be cleaned explicitly rather than silently merged.
