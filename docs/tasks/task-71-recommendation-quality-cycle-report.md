# Task 71 - Recommendation Quality Cycle Report

Status: planned

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

- Prefer a deterministic service that consumes persisted recommendations, combinations, latest worker status, and latest AI review.
- Keep the report paper-only and advisory.
- Avoid adding real-money readiness language.
- Treat the report as a diagnostic product surface, not as a betting command.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit
.\.venv\Scripts\python.exe -m ruff check app tests
cd dashboard
npm run test
npm run lint
npm run build
npm run smoke
```

## Next

Task 72 - Raw Versus Calibrated Recommendation Confidence.

## Blockers

No implementation blocker is known. The report should be designed before additional model changes so later calibration work has a stable measurement surface.

## Technical Debt

Current production audits require reading worker status, recommendations, guardrails, AI review, and logs separately. This task consolidates those views but does not improve model quality by itself.
