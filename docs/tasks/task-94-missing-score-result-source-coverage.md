# Task 94 - Missing-Score Result Source Coverage

Status: proposed

## Problem

Task 93 removed the live-feed retention blocker for current paper bets, but production now has one open paper bet whose Misli direct match detail endpoint returns a final event without score fields:

```text
paper_bet id=590
source_match_id=misli:football:2842605
diagnostic_reason=provider_result_missing_score
```

This is a different failure mode from retention. The system can find the final event identity, but the provider payload does not include enough score data to settle.

## Business Requirement

Paper-bet success-rate analysis needs truthful settlement outcomes. If Misli sometimes omits scores from final detail payloads, the system needs a second approved result source or a documented non-settleable terminal reason. It must not infer scores from odds, model confidence, or recommendation state.

## Scope

- Find a source that can resolve `misli:football:{event_id}` directly or match by teams, kickoff date, and competition with ambiguity rejection.
- Prefer a stable provider mapping over fuzzy text matching.
- Store fallback source provenance in the match result payload.
- Keep `provider_result_missing_score` visible in `/api/live/result-jobs`.
- Add tests for successful missing-score fallback, ambiguous fallback rejection, and terminal missing-score diagnostics.
- Run one Railway worker proof after deployment.

## Acceptance Criteria

- Production paper bet `590` either settles from a documented source or remains open with a precise non-settleable reason.
- No result is inferred without score proof.
- Production smoke stays green.
- The next audit can separate model performance from data-coverage failures.

## Notes

Railway CLI OAuth was expired during Task 93 verification, so deployment proof used public API and smoke checks. Re-auth Railway before the next deployment audit if service-level deployment metadata is needed.

## Implementation Note

The first Task 94 slice uses a curated external evidence registry, not live scraping. Browser/search access could read SportyTrader and Sofascore pages for the production fixture, but local runtime checks with `curl` and Python `urllib` were reset by SportyTrader. Relying on live scraping would make production behavior flaky.

For `misli:football:2842605`, the registry stores the SportyTrader source URL, capture time, and the relevant page excerpt:

```text
Gold Coast Knights
12/06/2026 11:30 Postponed
Brisbane City FC
```

The service now reopens `provider_result_missing_score` jobs when a curated external source exists. If the external source proves a non-played fixture, open paper bets for that match are voided with zero profit/loss and the source provenance is stored on the match payload. If no curated source exists or the source does not match teams/date, the existing `provider_result_missing_score` classification remains.

This is intentionally narrow. It fixes the known production research record without pretending the system has general historical result coverage.

## Completion Evidence

Verified on 2026-06-13.

Pushed to `main`:

```text
e53c889 Void curated postponed result fallback
```

Local verification:

```text
ruff: All checks passed.
pytest: 293 passed.
```

Production worker proof:

```text
latest collect_results run id=3796
started_at=2026-06-13T10:32:27.825686+00:00
status=completed
items_read=46
items_updated=2
items_skipped=45
errors_count=0
```

Production outcome:

```text
paper_bet id=590 source_match_id=misli:football:2842605 status=void profit_loss_units=0.0 settled_at=2026-06-13T10:32:27.824676+00:00
result_jobs.summary.retention_miss=0
result_jobs.summary.missing_score=0
open_paper_bets=1
settled_paper_bets=595
```

The remaining open paper bet is a new post-deployment record:

```text
paper_bet id=596 source_match_id=misli:football:2847018 status=open
```

Production smoke:

```text
ok=true
worker_status=fresh
worker_status.freshness_minutes=5
open_paper_bets=1
settled_paper_bets=595
```
