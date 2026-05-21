# Task 08 - Calibration And Bet Diagnostics

## Goal

Extend evaluation output so replay results show whether model probabilities and edges are meaningful, not just whether one run made profit.

## Requirements

Add bucket diagnostics to evaluation reports:

```text
probability_buckets
odds_buckets
edge_buckets
```

Each bucket should include:

```text
bets
wins
losses
voids
profit_loss_units
roi
average_odds
average_edge
brier_score
```

## Bucket Definitions

Probability buckets:

```text
0.00-0.10
0.10-0.20
0.20-0.30
0.30-0.40
0.40-0.50
0.50-0.60
0.60-0.70
0.70-0.80
0.80-0.90
0.90-1.00
```

Odds buckets:

```text
1.00-1.50
1.51-2.00
2.01-2.50
2.51-3.00
3.01-3.50
3.51+
```

Edge buckets:

```text
<0.02
0.02-0.04
0.04-0.06
0.06-0.08
0.08+
```

## Output

Include diagnostics in:

- `evaluation_runs.report_json`
- `reports/<report-name>_summary.json`

Console output can stay compact.

## Acceptance

Replay summary JSON contains all three diagnostic groups with non-empty bucket maps when bets exist.

