# Task 71 - Recommendation Quality Cycle Report

Status: completed

## Goal

Add an auditable per-cycle quality report for the live recommendation loop so every worker run explains what it produced, what it blocked, and why.

## Requirements

- Persist or expose a compact recommendation quality summary after each scheduled worker cycle.
- Include counts for actionable, watchlist, rejected, combinations, and blocked rows.
- Include distributions for expected value, edge, confidence, odds bands, risk flags, and freshness.
- Include the top actionable paper candidates and top blocked positive-EV rows.
- Distinguish fresh rows created in the current cycle from deduped rows still valid from a fresh snapshot.
- Make the summary available through API and CLI, and visible in the dashboard daily card area.

## Acceptance Criteria

- A worker cycle can be audited without manually querying several endpoints.
- The report explains why the dashboard is showing actionable rows, watchlist rows, or no rows.
- Guardrails and AI review can reference the same report instead of recomputing overlapping counts.
- Tests cover actionable, watchlist-only, all-rejected, and deduped-fresh cycle cases.

## Implementation Notes

Implemented in Task 71:

- Added `RecommendationQualityService` to build a deterministic cycle report from persisted recommendations, combinations, latest worker status, and latest AI recommendation review.
- Added `GET /api/live/recommendation-quality`.
- Added `recommendation-quality` CLI command for local or production database audits.
- Added dashboard data fetching and daily card display for cycle quality counts.
- Covered actionable, watchlist-only, all-blocked, and deduped-fresh snapshot cases.
- Kept the report paper-only and advisory.

## Verification

Completed:

```powershell
python -m pytest tests/unit/test_recommendation_quality_service.py tests/unit/test_dashboard_api.py::test_live_recommendation_quality_endpoint_reports_cycle_summary tests/integration/test_cli.py::test_recommendation_quality_command_reports_cycle_counts -q
python -m ruff check app tests
cd dashboard
npm run test -- api.test.ts --run
npm run lint
npm run build
```

Full production verification is completed after Railway API/dashboard deployment and dashboard smoke.

## Next

Task 72 - Raw Versus Calibrated Recommendation Confidence.

## Blockers

No implementation blocker remains.

## Technical Debt

This report consolidates production audit facts but does not improve model quality by itself. Task 72 should make confidence sources more explicit inside the report.
