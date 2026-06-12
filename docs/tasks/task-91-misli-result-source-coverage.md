# Task 91 - Misli Result Source Coverage

Status: completed

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

The follow-up production audit found two more queue-level bugs:

- Due jobs were ordered behind stale rows instead of prioritizing fresh/open paper-bet jobs.
- `next_attempt_at` was stored as text with mixed timezone offsets, so values like `2026-06-12T23:00:00+04:00` compared incorrectly against UTC `now` values.

Those were fixed by prioritizing open paper-bet result jobs, reopening terminal jobs when an open paper bet still depends on an incomplete match, exposing open-bet jobs first in `/api/live/result-jobs`, and normalizing result-job attempt times to UTC.

This task does not prove full historical result coverage. The current Misli live statistics feed settled a fresh finished event, but two older open paper bets still have `result not found in Misli response`. Task 93 should add a stronger approved fallback source or provider-retention strategy for those cases.

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

## Completion Evidence

Verified on 2026-06-13 Asia/Baku / 2026-06-12 UTC.

Pushed directly to `main` and deployed on Railway:

- `d87fa6f` - `Prioritize fresh Misli result jobs`
- `e98d6bf` - `Prioritize open paper bet results`
- `164349e` - `Reopen open paper bet result jobs`
- `55b5088` - `Recover unsettled open bet result jobs`
- `e3aeeaf` - `Normalize Misli result job attempt times`

Local verification:

```text
ruff: All checks passed.
pytest: 282 passed.
```

Production proof after `e3aeeaf` deployed:

```text
production-smoke: ok=true
worker_status=fresh freshness_minutes=0
open_paper_bets=2
settled_paper_bets=591
latest collect_results:
  started_at=2026-06-12T22:00:16.876874+00:00
  status=completed
  items_read=12
  items_updated=10
  items_skipped=2
  errors_count=0
```

The real deployed paper bet `593` (`misli:football:2845575`, Difaa Hassani El Jadidi vs Olympique Dcheira) settled automatically as `lost` after Misli reported a `2-2` draw:

```text
settled_at=2026-06-12T22:00:20.607709+00:00
profit_loss_units=-1.0
```

Remaining known limitation:

```text
paper_bet=590 result_job=2308 source_match_id=misli:football:2842605 status=pending last_error="result not found in Misli response"
paper_bet=589 result_job=2315 source_match_id=misli:football:2842611 status=pending last_error="result not found in Misli response"
```
