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

## Implementation Notes

Implemented in Task 61:

- Added `OperationalGuardrailService`.
- Added `GET /api/operations/guardrails`.
- Added `operational-status` CLI command.
- Added dashboard `Operational guardrails` panel.
- Guardrails include:
  - `worker_freshness`: warning for never-run, stale, or running worker; critical for failed worker.
  - `repeated_worker_failures`: critical after the configured consecutive failure threshold.
  - `provider_data_quality`: warning for parser drift, stale snapshot, low extraction confidence, or kickoff-date provider failures.
  - `ai_eval_safety`: critical for failed AI analysis or `ai_eval_failed` risk flags.
  - `recommendation_output`: warning when a fresh worker cycle produces zero recommendations.
- Each guardrail includes severity, state, observed value, threshold where relevant, and remediation text.

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

No code blocker remains. External notification destinations remain intentionally out of scope until dashboard/API guardrail status has been used in staging.

## Technical Debt

No notification integration was added. The alerting destination decision remains open in `docs/agent/04_OPEN_QUESTIONS.md`.
