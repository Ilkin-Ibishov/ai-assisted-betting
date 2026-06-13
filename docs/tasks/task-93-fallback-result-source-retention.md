# Task 93 - Fallback Result Source Retention

## Goal

Add reliable fallback coverage for finished Misli paper-bet outcomes that disappear from the current Misli live statistics response before settlement can collect them.

## Why

Task 91 proved that the result pipeline can now settle real deployed paper bets automatically when the Misli live statistics payload still contains the finished event. It also proved the remaining limitation: two open paper bets stayed unresolved because their event IDs were no longer present in the current Misli result payload.

Without fallback result retention, success-rate analysis and threshold-policy learning remain biased toward matches that finish and are collected inside the provider's short visibility window.

## Scope

- First slice: classify provider-retention misses explicitly when repeated Misli lookups for an open paper bet no longer find the event in the current feed.
- Identify an approved, auditable fallback result source for event IDs that Misli no longer returns.
- Prefer a source that can resolve by stable provider event ID; otherwise require deterministic team/date matching with ambiguity rejection.
- Store result provenance so each settled paper bet shows the source used.
- Keep unresolved outcomes pending or eventually `unresolvable`; do not infer results from odds movement, recommendation state, or confidence labels.
- Backfill only paper-bet research records; no real-money automation.
- Add diagnostics for provider retention misses so the dashboard can explain why a paper bet remains open.

## Acceptance Criteria

- At least one currently unresolved real production paper bet can either settle from an approved fallback source or be classified with a precise non-settleable reason.
- Result provenance is visible in stored match payloads or API output.
- Ambiguous fallback matches are rejected and logged.
- Tests cover successful fallback settlement, ambiguous fallback rejection, and missing-result retention diagnostics.
- Production smoke remains green after deployment.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_misli_result_service.py tests/unit/test_dashboard_api.py
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
```

After deployment, inspect:

```text
GET /api/live/result-jobs
GET /api/live/paper-bets
GET /api/live/status
GET /api/live/recommendation-quality
```

## Notes

This task should not weaken settlement truth standards. If the system cannot prove a result with a documented source and non-ambiguous identity match, the paper bet should remain unsettled and visible as a data-coverage gap.

## Implementation Note

The first implementation slice does not add an external fallback source. It adds a safer diagnostic foundation:

- Repeated not-found Misli result lookups for open paper bets are classified as `provider_retention_miss` after the provider window has plausibly passed.
- Classified retention misses stay terminal instead of being reopened every worker cycle.
- `/api/live/result-jobs` exposes `diagnostic_reason` and a `retention_miss` summary count.
- The paper bet remains open; no result is inferred.

The next slice should choose and wire an approved fallback source with provenance and ambiguity rejection.

## First-Slice Completion Evidence

Verified on 2026-06-13.

Pushed to `main`:

```text
af6b737 Classify Misli result retention misses
```

Local verification:

```text
ruff: All checks passed.
pytest: 284 passed.
```

Production API deployed the new diagnostic fields. Railway CLI metadata verification was blocked by expired OAuth (`invalid_grant`), so deployment proof used public API behavior and production smoke.

Production smoke:

```text
ok=true
api_health=ok
live_status.latest_run_status=completed
worker_status=fresh
worker_status.freshness_minutes=0
open_paper_bets=2
settled_paper_bets=593
```

Worker proof:

```text
latest collect_results run id=3776
started_at=2026-06-13T08:32:11.460263+00:00
status=completed
items_read=34
items_updated=1
items_skipped=33
errors_count=0
```

Result-job diagnostics after the worker run:

```text
summary.due=0
summary.retention_miss=2
paper_bet result_job=2308 source_match_id=misli:football:2842605 diagnostic_reason=provider_retention_miss
paper_bet result_job=2315 source_match_id=misli:football:2842611 diagnostic_reason=provider_retention_miss
```

The two paper bets remain open because no approved result source proved their outcomes. That is intentional; this slice made the data-coverage gap explicit rather than inventing settlement outcomes.
