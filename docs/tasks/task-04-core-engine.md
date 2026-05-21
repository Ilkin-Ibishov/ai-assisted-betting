# Codex Task 04 — Core Engine

## Goal

Implement feature generation, prediction generation, value detection, and paper bet writing.

## Files

Create/modify:

```text
app/core/feature_builder.py
app/core/prediction_engine.py
app/core/value_detector.py
app/core/paper_bet_logger.py
app/services/prediction_service.py
app/cli.py
```

## FeatureBuilder

Implement baseline features:

```text
home_form_points_5
away_form_points_5
home_goals_for_avg_5
away_goals_for_avg_5
home_goals_against_avg_5
away_goals_against_avg_5
home_advantage_flag
bookmaker_probability
bookmaker_margin_estimate
```

## PredictionEngine

Implement:

```text
BaselineHeuristicPredictionEngine
```

Use the logic in `08_PREDICTION_ENGINE.md`.

## ValueDetector

Use config:

```text
MIN_EDGE
MIN_ODDS
MAX_ODDS
DEFAULT_STAKE_UNITS
```

## PaperBetLogger

Write fake bets only.

Avoid duplicates.

## CLI

Implement:

```bash
python -m app.cli generate-features
python -m app.cli generate-predictions
python -m app.cli write-paper-bets
```

## Acceptance

After sample import:

```bash
python -m app.cli generate-features
python -m app.cli generate-predictions
python -m app.cli write-paper-bets
```

DB contains:

```text
features
predictions
paper_bets if value rule passes
decision_logs
```

## Tests

Add unit tests for:

```text
feature builder
prediction engine
value detector
paper bet logger
```
