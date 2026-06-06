# Task 81 - Production Behavior Monitor

Status: completed

## Goal

Make the current production loop explain itself without manually joining worker status, snapshots, recommendations, AI reviews, threshold reviews, and journals.

## Requirements

- Add a read-only service that summarizes end-to-end loop behavior.
- Report worker, snapshot, recommendation, AI review, threshold review, and journal stages.
- Mark missing, stale, failed, empty, and incomplete stages as warning or critical.
- Expose the summary through the API for dashboard consumption.
- Surface the summary on the dashboard as a compact operations panel.

## Implementation Notes

- Added `ProductionBehaviorService`.
- Added `GET /api/operations/behavior`.
- Added dashboard API types and `fetchProductionBehavior()`.
- Added a `Loop behavior` dashboard panel with stable stage tiles.
- The monitor uses existing persisted facts; it does not call public endpoints internally.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_production_behavior_service.py tests/unit/test_dashboard_api.py tests/unit/test_worker_monitoring_service.py tests/unit/test_scheduled_paper_worker_service.py -q
.\.venv\Scripts\python.exe -m ruff check app tests
cd dashboard
npm run test -- --run src/lib/api.test.ts
npm run build
```

## Next

Deploy API and dashboard, then smoke `GET /api/operations/behavior` and verify the public dashboard renders the new loop behavior panel.
