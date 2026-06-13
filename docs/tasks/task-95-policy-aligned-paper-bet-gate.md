# Task 95 - Policy-Aligned Paper-Bet Gate

Status: completed

## Problem

After Task 94 cleared the old result-coverage blockers, production still created a new open paper bet:

```text
paper_bet id=596
source_match_id=misli:football:2847018
confidence_score=0.133333
risk_flags=low_confidence,past_kickoff_open
```

At the same time, recommendation governance reported:

```text
overall_state=watchlist_only
actionable_count=0
confidence.low=500
ai_review.approval_state=reject
threshold_policy.decision=fail_closed
```

That means the paper-bet writer was using a looser gate than the recommendation/AI review layer. The system could keep creating low-confidence cold-start research bets even when the current policy view says nothing is actionable.

## Audit Findings

- Result coverage is no longer the primary blocker: `provider_retention_miss=0` and `provider_result_missing_score=0`.
- The latest daily journal is `settled_learning`, but the review still rejects promotion because all reviewed recommendations are low-confidence.
- The latest bet ledger has only a tiny clean resulted sample for the current window: 2 resulted bets, 1 open needs-result bet, and paper P/L of `-0.12`.
- The broad latest-paper-bets endpoint is dominated by historic voided cleanup rows, so it should not be used alone for model ROI decisions.

## Decision

Raise `PaperBetLogger`'s creation confidence floor from `0.1` to `0.5`, matching the active/default recommendation governance floor. This prevents watchlist-only cold-start rows from becoming new paper-bet samples.

This does not disable paper betting globally. Higher-confidence `BET` predictions still create paper bets, and already-open bets still settle normally.

## Verification

```text
pytest tests/unit/test_paper_bet_logger.py tests/unit/test_live_cycle_service.py tests/unit/test_scheduled_paper_worker_service.py -q
pytest tests/unit/test_recommendation_service.py tests/unit/test_recommendation_quality_service.py -q
```

Both focused suites pass locally.

## Production Proof Plan

After deployment, wait for one scheduled worker cycle and verify:

```text
GET /api/live/recommendation-quality
GET /api/live/bet-ledger?status=all&include_voided=true
GET /api/live/paper-bets
```

Expected behavior: if the cycle remains watchlist-only with max confidence below `0.5`, no new paper bet should be created. Existing open bet `596` may still settle later; that is separate from creation gating.

## Completion Evidence

Verified on 2026-06-13.

Pushed to `main`:

```text
7feed11 Align paper bet confidence gate with policy
```

Local verification:

```text
ruff: All checks passed.
pytest: 294 passed.
```

Production worker proof after deployment:

```text
latest_worker_run.id=3797
started_at=2026-06-13T11:01:04.071446+00:00
status=completed
items_created=0
items_skipped=568
errors_count=0
```

Recommendation quality during the proof cycle:

```text
overall_state=watchlist_only
actionable_count=0
confidence.low=500
ai_review.approval_state=reject
ai_review.model_quality.max_confidence_score=0.133333
```

Paper-bet proof:

```text
latest paper_bet id remains 596
paper_bet id=596 status=open confidence_score=0.133333 risk_flags=low_confidence,past_kickoff_open
no post-deployment paper bet id > 596 was created
```

Production smoke:

```text
ok=true
worker_status=fresh
open_paper_bets=1
settled_paper_bets=595
```

The remaining open paper bet predates this policy change. The creation leak is closed; the remaining work is to let existing bet `596` settle or retire through the normal result path.

## Final Post-Settlement Evidence

Verified later on 2026-06-13 after the normal result pipeline settled the remaining pre-policy bet.

Production state:

```text
latest collect_results run id=3871
started_at=2026-06-13T18:01:15.666456+00:00
status=completed
items_read=50
items_updated=6
errors_count=0

open_paper_bets=0
settled_paper_bets=596
result_jobs.retention_miss=0
result_jobs.missing_score=0
```

Paper bet `596` settled normally:

```text
paper_bet id=596
source_match_id=misli:football:2847018
status=lost
profit_loss_units=-1.0
settled_at=2026-06-13T12:00:55.230890+00:00
confidence_score=0.133333
```

Current learning state:

```text
overall_state=watchlist_only
actionable_count=0
confidence.low=500
ai_review.approval_state=reject
daily_journal.open_paper_bets=[]
daily_journal.settled_count=8
bet_ledger.paper_profit_loss=-1.12
bet_ledger.win_rate=0.333333
```

Production smoke:

```text
ok=true
worker_status=fresh
open_paper_bets=0
settled_paper_bets=596
```

The system is now fail-closed: it continues to generate watchlist/rejected research rows, but it does not create new paper bets from low-confidence cold-start output.
