# Task 16 - Comparison Ranking

## Goal

Make comparison reports easier to interpret by adding ranking annotations for profitability and calibration.

## Requirements

Add a `rankings` object to comparison JSON:

```json
{
  "best_roi": {...},
  "best_brier_score": {...},
  "best_log_loss": {...}
}
```

Each winner should include:

```text
model
bookmaker
value
```

Add rank columns to comparison CSV:

```text
roi_rank
brier_score_rank
log_loss_rank
```

Ranking rules:

- Higher ROI is better.
- Lower Brier score is better.
- Lower log loss is better.
- `null` metrics rank last.

## Acceptance

Comparison JSON identifies best runs by ROI, Brier score, and log loss. Comparison CSV includes rank columns.

## Implementation Notes

Implemented in `app/services/comparison_service.py`.

What was done:

- Comparison runs are annotated with `roi_rank`, `brier_score_rank`, and `log_loss_rank`.
- Comparison JSON now includes a top-level `rankings` object with `best_roi`, `best_brier_score`, and `best_log_loss`.
- Ranking rules are covered by a focused unit test, including null metrics ranking last.
- The CLI comparison integration test verifies the JSON rankings and CSV rank columns.

What's next:

- Triage open comparison technical debt before adding a broader UI or live collection layer.

Blockers:

- None.

Technical debt:

- Existing comparison cleanup and sequential execution debt remains tracked in `docs/agent/05_TECHNICAL_DEBT.md`.
