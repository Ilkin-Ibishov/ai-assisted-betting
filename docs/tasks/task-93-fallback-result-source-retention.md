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

The first implementation slice did not add an external fallback source. It added a safer diagnostic foundation:

- Repeated not-found Misli result lookups for open paper bets are classified as `provider_retention_miss` after the provider window has plausibly passed.
- Classified retention misses stay terminal instead of being reopened every worker cycle.
- `/api/live/result-jobs` exposes `diagnostic_reason` and a `retention_miss` summary count.
- The paper bet remains open; no result is inferred.

The next slice should choose and wire an approved fallback source with provenance and ambiguity rejection.

The next investigation found a provider-native fallback in the Misli web bundle:

```text
GET https://apivx.misli.az/api/web/v1/statistics/sportType/SOCCER/match/{event_id}
```

This endpoint resolves by the existing Misli/Betradar event id (`sgi`) and therefore avoids fuzzy team/date settlement. The second slice wires this endpoint after the current live-feed result lookup:

- Use the current live statistics feed first.
- If an open paper-bet job is not found there, fetch Misli direct match detail by `misli_event_id`.
- Settle only when the direct detail payload returns final status and both scores.
- If the direct detail payload is final but has no score fields, classify `provider_result_missing_score`.
- Keep all behavior paper-only and provenance-bearing through `raw_result`.

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

## Direct-Detail Completion Evidence

Verified on 2026-06-13.

Pushed to `main`:

```text
79867c2 Use Misli match detail result fallback
82c147d Harden Misli result fallback reopening
```

Local verification:

```text
ruff: All checks passed.
pytest: 290 passed.
```

Production worker proof after the hardening deployment:

```text
latest collect_results run id=3786
started_at=2026-06-13T09:31:43.620355+00:00
status=completed
items_read=7
items_updated=2
items_skipped=5
errors_count=0
```

Production smoke:

```text
ok=true
worker_status=fresh
worker_status.freshness_minutes=0
open_paper_bets=1
settled_paper_bets=594
```

Outcome proof:

```text
result_jobs.summary.retention_miss=0
result_jobs.summary.missing_score=1
paper_bet id=589 source_match_id=misli:football:2842611 status=lost profit_loss_units=-1.0 settled_at=2026-06-13T09:31:49.489353+00:00
result_job id=2308 source_match_id=misli:football:2842605 diagnostic_reason=provider_result_missing_score
```

The direct Misli detail endpoint proved `misli:football:2842611` and allowed settlement. The remaining open production paper bet, `misli:football:2842605`, is no longer a provider-retention miss; the provider-native detail endpoint returns final status without usable score fields, so the system correctly exposes it as `provider_result_missing_score`.

## Audit Corrections

The original first-slice decision to keep `provider_retention_miss` terminal was too conservative once a provider-native direct-detail endpoint was discovered. That decision was reversed so open paper bets can be reopened and retried against the fallback.

The first direct-detail implementation missed a production-shaped path: older completed/no-score matches with open paper bets could be skipped by pre-retirement before the fallback was attempted. The hardening commit makes open paper-bet jobs flow through the main due loop, where fallback lookup and missing-score classification happen with tests.

The current result architecture is now closer to the business requirement: it settles when a trusted source proves the score, and it records a precise blocker when the source cannot provide enough data. It still does not yet create a large enough clean settlement sample for probability learning by itself; that remains a next task.
