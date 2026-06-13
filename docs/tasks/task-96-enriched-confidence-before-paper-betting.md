# Task 96 - Enriched Confidence Before Paper Betting

Status: proposed

## Problem

The operational loop is now coherent and fail-closed:

```text
open_paper_bets=0
provider_retention_miss=0
provider_result_missing_score=0
recommendation_quality.overall_state=watchlist_only
recommendation_quality.actionable_count=0
recommendation_quality.confidence.low=500
ai_review.approval_state=reject
```

Task 95 correctly blocks new low-confidence cold-start paper bets. That leaves the system safe, but not yet useful for learning. The model is still mostly producing odds-only, cold-start confidence around `0.133333`, so nothing reaches the paper-bet confidence floor.

## Business Requirement

The system should resume paper-bet sample creation only when a recommendation has enough evidence to be meaningfully evaluated. That means improving feature enrichment and confidence quality before loosening gates.

## Scope

- Audit why recent Misli recommendations remain cold-start despite the existing external-context feature work.
- Identify the missing mapping between Misli teams/leagues and the external context source.
- Add or improve alias/normalization coverage for current live Misli teams.
- Keep paper-bet creation blocked for `confidence_score < 0.5`.
- Prove that any resumed paper-bet creation comes from enriched or otherwise confidence-justified records, not raw cold-start rows.

## Acceptance Criteria

- Recommendation quality reports at least one medium/high-confidence candidate, or documents why no current live events can be enriched.
- New paper bets are created only when confidence is at least `0.5`.
- AI review no longer rejects solely because every candidate is cold-start low-confidence.
- Production smoke remains green.

## Notes

Do not lower the confidence floor to create more samples. The previous low-confidence sample mode produced fast data, but it mixed model weakness with data-quality repair work and created noisy paper-bet records. The next improvement should increase signal quality, not relax the gate.
