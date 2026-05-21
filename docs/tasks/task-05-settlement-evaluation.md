# Codex Task 05 — Settlement and Evaluation

## Goal

Implement paper bet settlement and evaluation reporting.

## Files

Create/modify:

```text
app/core/result_settler.py
app/core/evaluator.py
app/services/settlement_service.py
app/services/evaluation_service.py
app/cli.py
```

## Settlement

Support:

```text
1X2
OVER_UNDER_2_5
```

MVP may only have 1X2 sample data, but code should be structured for both.

## Evaluation

Calculate:

```text
total_bets
settled_bets
wins
losses
voids
hit_rate
profit_loss_units
roi
average_odds
average_edge
brier_score
log_loss
```

Store result in:

```text
evaluation_runs
```

Print console summary.

## CLI

Implement:

```bash
python -m app.cli settle-results
python -m app.cli evaluate
```

## Acceptance

Full flow works:

```bash
python -m app.cli init-db
python -m app.cli import-sample-data
python -m app.cli generate-features
python -m app.cli generate-predictions
python -m app.cli write-paper-bets
python -m app.cli settle-results
python -m app.cli evaluate
```

## Tests

Add integration test for full pipeline.
