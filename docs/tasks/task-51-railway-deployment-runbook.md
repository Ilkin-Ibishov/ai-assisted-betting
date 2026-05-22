# Task 51 - Railway Deployment Runbook And Production Smoke

## Goal

Document and verify the Railway deployment process end to end.

## Requirements

- Write Railway setup steps.
- Document services, environment variables, build commands, start commands, migrations, and smoke checks.
- Include rollback and recovery notes.
- Run production-like smoke tests against the deployed or staging URL.
- Keep paper-only safety boundaries visible.

## Acceptance Criteria

- A new operator can deploy the project from the runbook.
- API health, dashboard load, live status, and dry-run visibility are smoke-tested.
- Deployment does not require local-only files except documented fixtures.
- Known limitations are documented.

## Implementation Notes

Implemented in Task 51:

- Added `ProductionSmokeService` with stdlib HTTP checks for deployed API and dashboard URLs.
- Added `production-smoke` CLI command.
- Smoke checks cover `/api/health`, `/api/live/status`, `/api/live/runs?limit=5`, `/api/reports/comparisons`, and optional dashboard HTML root.
- Expanded `docs/deployment/railway-readiness.md` into an operator runbook with API, dashboard, Postgres, worker boundary, staging smoke, rollback, and recovery notes.
- Kept scheduled live collection disabled by default until Task 60 monitoring exists.

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

Task 60 - Railway Worker Deployment And Monitoring.

## Blockers

No code blocker remains. Running smoke against real Railway staging requires deployed Railway service URLs and credentials.

## Technical Debt

No new implementation debt. Manual Railway project creation and first deployed smoke evidence remain operational steps until Railway credentials are available.
