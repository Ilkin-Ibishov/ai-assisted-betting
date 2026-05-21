# 08 — Prediction Engine

## MVP Principle

Use a baseline prediction engine first.

The first version should prove the pipeline, not beat the market.

## Interface

Create:

```text
app/core/prediction_engine.py
```

Suggested structure:

```python
from abc import ABC, abstractmethod
from app.schemas.prediction import PredictionInput, PredictionOutput


class PredictionEngine(ABC):
    model_name: str
    model_version: str

    @abstractmethod
    def predict(self, prediction_input: PredictionInput) -> PredictionOutput:
        pass
```

## MVP Model

Use:

```text
BaselineHeuristicPredictionEngine
```

Model name:

```text
baseline_heuristic
```

Model version:

```text
v0
```

## Baseline Logic

For each selection:

1. Start from bookmaker normalized probability.
2. Apply small adjustments based on simple features.
3. Clamp probability between minimum and maximum.
4. Return model probability.

Example for HOME selection:

```text
base = bookmaker_probability

form_diff = home_form_points_5 - away_form_points_5
goal_diff = (home_goals_for_avg_5 - home_goals_against_avg_5) - (away_goals_for_avg_5 - away_goals_against_avg_5)

adjustment = 0.01 * form_diff + 0.02 * goal_diff + 0.02 home advantage

model_probability = clamp(base + adjustment, 0.05, 0.85)
```

This is intentionally simple.

Do not pretend it is a profitable model.

## Confidence Score

MVP confidence score:

```text
confidence_score = min(abs(edge) / 0.15, 1.0)
```

Later, improve this.

## Prediction Output

Prediction must include:

```text
match_id
market
selection
model_name
model_version
model_probability
bookmaker_probability
edge
confidence_score
decision
reason
```

## Calibration Warning

The model probability is not trustworthy until evaluated.

Do not use model probability for real-money decisions.

## Future Models

Later possible engines:

### 1. Logistic Regression

Requires historical/replay data.

### 2. Elo Rating Model

Good simple model for team strength.

MVP implementation:

```text
model_name = elo
model_version = v0
initial_rating = 1500
k_factor = 20
home_advantage = 65
```

Elo must only use matches completed before the candidate match kickoff.

These values are configurable through:

```env
ELO_INITIAL_RATING
ELO_K_FACTOR
ELO_HOME_ADVANTAGE
```

### 3. Poisson Goals Model

Useful for Over/Under and scoreline probabilities.

### 4. Ensemble

Only after baseline models are stable.

## Do Not Use LLM As Final Predictor

LLM can help with:

- Explanation
- News summarization
- Log analysis
- Feature suggestions

LLM must not be the first final decision engine.
