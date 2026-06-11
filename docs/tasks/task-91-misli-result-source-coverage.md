# Task 91 - Misli Result Source Coverage

## Goal

Make deployed paper bets settle automatically from reliable finished-match results, so the system can measure success rate and feed threshold-policy learning.

## Why

Task 90 proved that the live worker can now create low-confidence positive-EV paper samples. The first post-deploy Railway worker cycle created a new open paper bet, but result jobs still stayed pending with `result not found in Misli response`.

That means the current blocker has moved from paper-bet creation to result-source coverage. The existing Misli result fetch path appears to cover live/current statistics, not historical finished events already queued for settlement.

## Scope

- Audit the current Misli result collection path and confirm which endpoint or payload can resolve finished event IDs.
- Prefer a public, unauthenticated, robots-aware Misli result source if available.
- If Misli does not expose stable historical public results, add a vetted fallback result source with deterministic match identity/provenance.
- Store enough provenance to explain which source settled each paper bet.
- Mark unreachable stale result jobs distinctly from retryable pending jobs.
- Keep all behavior paper-only.

## Acceptance Criteria

- A Railway worker cycle can complete at least one result job for a real deployed paper bet after kickoff.
- Settled paper bets increase without manual database edits.
- Threshold review sample size can grow from settled production paper records.
- Result-job API/reporting distinguishes `pending`, `completed`, and stale/unresolvable jobs.
- Tests cover successful result lookup, not-found retry behavior, and stale/unresolvable classification.

## Implementation Note

The first code slice retires stale `result not found in Misli response` jobs as `unresolvable` after repeated misses and more than two days after kickoff. This prevents old result jobs from consuming the worker's per-cycle limit forever and lets fresh recently-finished matches reach the current Misli result feed while they are still available.

This does not yet prove full historical result coverage. If fresh finished matches still fail to settle after stale queue cleanup, the next slice must add a stronger approved result source.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_live_result_collector.py tests/unit/test_scheduled_paper_worker_service.py tests/unit/test_dashboard_api.py -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
```

After deployment, run production smoke and inspect:

```text
/api/live/result-jobs
/api/live/status
/api/live/recommendation-quality
```

## Notes

Do not loosen settlement rules to infer outcomes from odds movement or recommendation status. If a result cannot be proven by an approved source, keep the paper bet unsettled and make the blocker visible.
