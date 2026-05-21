# Task 61 - Operational Guardrails And Alerting

## Goal

Add operational guardrails so stale data, broken scraping, unsafe AI output, and failing workers are visible before recommendations become misleading.

## Requirements

- Add alert-worthy states for stale provider data, repeated collection failures, AI eval failures, empty recommendation cycles, and database errors.
- Surface guardrails in dashboard status panels.
- Add CLI/API endpoints for operational status.
- Record clear remediation hints in logs and docs.
- Do not add notification bots until dashboard and API guardrail status are stable.

## Acceptance Criteria

- Operators can tell whether the system is healthy enough to trust paper recommendations.
- Guardrail status distinguishes warning from critical failure.
- Tests cover stale data, repeated worker failure, unsafe AI output, and empty recommendation runs.
- Docs explain what each guardrail means and what to check next.

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

Task 62 - Final Production Readiness Review.

## Blockers

Requires deployed worker monitoring and recommendation dashboard.

## Technical Debt

Track any alerting destination decision as an open question until the project needs proactive external notifications.
