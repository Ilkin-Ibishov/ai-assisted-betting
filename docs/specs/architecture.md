# 03 — Architecture

## High-Level Flow

```text
DataProvider
    ↓
Normalizer
    ↓
Storage
    ↓
FeatureBuilder
    ↓
PredictionEngine
    ↓
ValueDetector
    ↓
PaperBetLogger
    ↓
ResultSettler
    ↓
Evaluator
```

## Dashboard Direction

The analytical dashboard is the next product phase after the offline/replay research core.

Accepted stack:

```text
Frontend: React + TypeScript + Vite
UI: shadcn/ui + Tailwind CSS
Charts: Recharts
Tables: TanStack Table
Data fetching/state: TanStack Query
API layer: FastAPI
```

The dashboard should read from a local FastAPI layer backed by existing SQLite data and `reports/*.json` artifacts. The first dashboard version should be read-only.

## Components

### 1. DataProvider

Responsible for retrieving raw match, odds, and result data.

Examples:

```text
SampleProvider
ManualCSVProvider
LiveAPIProvider
HistoricalCSVProvider
ReplayProvider
```

### 2. Normalizer

Converts provider-specific payloads into internal schemas.

Responsibilities:

- Normalize team names
- Normalize market names
- Normalize selections
- Validate dates
- Validate odds
- Attach source metadata

### 3. Storage

SQLite for MVP.

Stores:

- matches
- odds snapshots
- features
- predictions
- paper bets
- decision logs
- source payloads

### 4. FeatureBuilder

Creates features from stored match/odds/history data.

MVP features:

```text
home_form_points_5
away_form_points_5
home_goals_for_avg_5
away_goals_for_avg_5
home_goals_against_avg_5
away_goals_against_avg_5
home_advantage_flag
implied_probability
bookmaker_margin_estimate
```

### 5. PredictionEngine

Produces model probabilities.

MVP engine:

```text
BaselineHeuristicPredictionEngine
```

Later:

```text
LogisticRegressionPredictionEngine
EloPredictionEngine
PoissonPredictionEngine
```

### 6. ValueDetector

Compares model probability against bookmaker implied probability.

MVP rule:

```text
edge = model_probability - bookmaker_probability

paper bet if:
edge >= min_edge
and odds between min_odds and max_odds
```

### 7. PaperBetLogger

Writes fake bets only.

Stores:

```text
selection
odds_taken
stake_units
expected_value
decision_reason
```

### 8. ResultSettler

Settles paper bets after match result is known.

Calculates:

```text
profit_loss_units
status
closing_odds
clv
```

### 9. Evaluator

Produces reports:

```text
total_bets
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
bets_by_odds_range
bets_by_market
```

## Module Layout

Recommended structure:

```text
paper-odds-lab/
  app/
    __init__.py
    cli.py
    config.py

    db/
      __init__.py
      engine.py
      models.py
      repositories.py
      migrations.py

    providers/
      __init__.py
      base.py
      sample_provider.py
      manual_csv_provider.py
      historical_csv_provider.py
      live_api_provider.py

    normalizers/
      __init__.py
      match_normalizer.py
      odds_normalizer.py
      result_normalizer.py

    core/
      __init__.py
      feature_builder.py
      prediction_engine.py
      value_detector.py
      paper_bet_logger.py
      result_settler.py
      evaluator.py

    schemas/
      __init__.py
      match.py
      odds.py
      prediction.py
      paper_bet.py

    services/
      __init__.py
      collection_service.py
      prediction_service.py
      settlement_service.py
      evaluation_service.py
      analysis_service.py

    utils/
      __init__.py
      time.py
      probabilities.py
      logging.py

  data/
    sample/
    imports/
    exports/

  reports/

  dashboard/
    package.json
    src/

  tests/
    unit/
    integration/

  docs/
```

## Dependency Direction

Allowed:

```text
cli -> services -> core -> repositories -> db
providers -> normalizers -> repositories
```

Avoid:

```text
core -> providers
core -> CLI
db models -> providers
```

Core logic must not depend on live provider implementation.
