# 10 — Logging and Evaluation

## Logging Principle

Every decision must be explainable after the fact.

If a paper bet is created, the system must store enough information to answer:

```text
Why did this bet exist?
What data was used?
What odds were available?
What was the model probability?
What rule triggered the bet?
What happened after settlement?
```

## Logging Types

### 1. Application Logs

Console/file logs for runtime debugging.

### 2. Decision Logs

DB logs for decision audit.

Use the `decision_logs` table.

### 3. Live Run Registry

DB records for operational run status.

Use the `live_runs` table for every manual live collection or live paper cycle command.

Minimum run fields:

```text
run_id
run_type
provider
league
season
status
started_at
finished_at
items_read
items_created
items_updated
items_skipped
errors_count
error_summary
model_name
```

The registry is for process-level status. Keep record-level audit details in `decision_logs` or raw payload fields.

## Required Decision Logs

Log at these stages:

```text
COLLECT_MATCHES
COLLECT_ODDS
NORMALIZE_MATCH
NORMALIZE_ODDS
BUILD_FEATURES
PREDICT
VALUE_DETECTION
WRITE_PAPER_BET
SETTLE_RESULT
EVALUATE
```

## Log Levels

```text
INFO
WARNING
ERROR
```

## Evaluation Metrics

### 1. Total Bets

```text
count(paper_bets)
```

### 2. Hit Rate

```text
wins / settled_bets
```

### 3. Profit/Loss Units

```text
sum(profit_loss_units)
```

### 4. ROI

```text
profit_loss_units / total_staked_units
```

### 5. Average Odds

```text
avg(odds_taken)
```

### 6. Average Edge

```text
avg(edge)
```

### 7. Brier Score

For binary selections:

```text
(predicted_probability - actual_outcome)^2
```

Average across settled bets.

### 8. Log Loss

Use safe clipping:

```text
p = clamp(model_probability, 0.001, 0.999)
```

Then:

```text
-(y * log(p) + (1-y) * log(1-p))
```

### 9. Odds Range Breakdown

Buckets:

```text
1.00 - 1.50
1.51 - 2.00
2.01 - 2.50
2.51 - 3.00
3.01 - 3.50
3.51+
```

### 10. Market Breakdown

Group by:

```text
market
```

### 11. League Breakdown

Group by:

```text
league
```

## Minimum Evaluation Report

Console output:

```text
Evaluation Run
--------------
Total bets:
Settled bets:
Wins:
Losses:
Voids:
Hit rate:
Total staked:
Profit/Loss:
ROI:
Average odds:
Average edge:
Brier score:
Log loss:
```

Also save JSON report to `evaluation_runs.report_json`.

## Diagnostic Buckets

Evaluation JSON should include:

```text
probability_buckets
odds_buckets
edge_buckets
```

Each bucket should report:

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

## Model Configuration Metadata

Evaluation JSON should include `model_config`:

```json
{
  "model_name": "elo",
  "model_version": "v0",
  "elo_initial_rating": 1500,
  "elo_k_factor": 20,
  "elo_home_advantage": 65
}
```

This metadata is required for reproducible replay and comparison reports.

## Comparison Ranking Reports

Replay comparison JSON should include a top-level `rankings` object:

```json
{
  "best_roi": {"model": "elo", "bookmaker": "Avg", "value": 0.08},
  "best_brier_score": {"model": "baseline_heuristic", "bookmaker": "B365", "value": 0.21},
  "best_log_loss": {"model": "elo", "bookmaker": "B365", "value": 0.63}
}
```

Comparison CSV rows should include:

```text
roi_rank
brier_score_rank
log_loss_rank
```

Higher ROI ranks better. Lower Brier score and lower log loss rank better. Missing metrics rank last.

## Comparison Analysis Reports

`analyze-comparison` should read comparison JSON and print:

```text
comparison metadata
winners
sample-size warning
interpretation notes
next experiment guidance
```

Small samples below 300 settled bets are exploratory and should not be trusted as evidence of an edge. Samples from 300 to 499 settled bets are directionally useful but not conclusive. Samples at or above 500 settled bets are more useful for comparison but still not proof of future profit.

## Dashboard Reporting Contract

The analytical dashboard should consume comparison report data through the Dashboard Data API and display:

```text
metadata
rankings
runs
analysis
```

Dashboard views should preserve the same interpretation rules used by `analyze-comparison`.

## Interpretation Rules

### ROI Positive, CLV Negative

Likely short-term luck.

### ROI Negative, CLV Positive

May be variance. Continue testing.

### Bad Brier Score

Probability estimates are poorly calibrated.

### Strong Performance in Tiny Sample

Do not trust it.

Minimum meaningful sample:

```text
300-500 settled paper bets
```
