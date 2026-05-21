# 01 — Project Brief

## Project Name

Paper Odds Lab

## Problem

The user wants to evaluate whether a structured betting decision system can identify value opportunities in football odds.

The system must first operate in paper mode, with fake stake units and full logging.

## Main Idea

Instead of building an "AI betting bot", build a **sports odds research engine**:

```text
Data -> Features -> Probability -> Value Detection -> Paper Bet -> Settlement -> Evaluation
```

## Success Criteria

The MVP is successful if it can:

1. Store football matches.
2. Store odds snapshots with timestamps.
3. Generate basic features.
4. Produce model probabilities.
5. Detect value candidates.
6. Write paper bets.
7. Settle paper bets after results are available.
8. Produce evaluation metrics.
9. Log every decision step.

## Non-Goals

The project is not successful just because it picks winners.

The project is successful only if it produces measurable, auditable, repeatable decisions.

## Key Risks

### 1. Data Quality Risk

Bad odds or wrong match mapping will destroy evaluation quality.

Mitigation:

- Strict source IDs
- Unique constraints
- Raw payload storage
- Validation checks
- Snapshot timestamps

### 2. Model Overconfidence

A model may output probabilities that look precise but are not calibrated.

Mitigation:

- Track Brier score
- Track log loss
- Track probability buckets
- Track decision logs

### 3. Short Sample Illusion

100 paper bets are not enough.

Mitigation:

- Treat early results as debugging, not proof
- Target 300–500 paper bets before making strong claims

### 4. Legal / ToS Risk

Protected bookmaker scraping creates account and legal risk.

Mitigation:

- Use official APIs or permitted sources
- Do not bypass bot detection
- Do not automate real-money betting

## MVP Acceptance Definition

The MVP is acceptable when the following command sequence works locally:

```bash
python -m app.cli init-db
python -m app.cli import-sample-data
python -m app.cli generate-features
python -m app.cli generate-predictions
python -m app.cli write-paper-bets
python -m app.cli settle-sample-results
python -m app.cli evaluate
```

And produces:

```text
- matches in DB
- odds snapshots in DB
- features in DB
- predictions in DB
- paper bets in DB
- decision logs in DB
- evaluation report in console or CSV
```
