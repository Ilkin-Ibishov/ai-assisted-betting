# 07 — Feature Engineering

## MVP Principle

Start with simple, explainable features.

Do not introduce complex ML features until the pipeline works.

## Feature Versioning

Every feature row must have:

```text
feature_version
```

Initial value:

```text
v0_baseline
```

When feature logic changes, create a new version.

Do not overwrite old feature outputs silently.

## MVP Features

### 1. Home Form Points Last 5

For the home team's last 5 completed matches before kickoff:

```text
win = 3
draw = 1
loss = 0
```

Store average or total.

Recommended:

```text
home_form_points_5
```

### 2. Away Form Points Last 5

Same for away team.

```text
away_form_points_5
```

### 3. Goals For Average Last 5

```text
home_goals_for_avg_5
away_goals_for_avg_5
```

### 4. Goals Against Average Last 5

```text
home_goals_against_avg_5
away_goals_against_avg_5
```

### 5. Home Advantage Flag

```text
home_advantage_flag = 1
```

For 1X2 selections, this can be useful later.

### 6. Bookmaker Probability

From decimal odds:

```text
implied_probability = 1 / odds_decimal
```

### 7. Bookmaker Margin Estimate

For 1X2 market:

```text
margin = sum(implied_probabilities_for_HOME_DRAW_AWAY) - 1
```

For Over/Under 2.5:

```text
margin = sum(implied_probabilities_for_OVER_UNDER) - 1
```

## Probability Normalization

Bookmaker probabilities contain margin.

For market probabilities, normalize:

```text
normalized_probability = raw_implied_probability / sum(raw_implied_probabilities_for_market)
```

Store both if possible:

```text
raw_implied_probability
normalized_bookmaker_probability
```

For MVP schema, `bookmaker_probability` can mean normalized probability.

## Data Leakage Rule

FeatureBuilder must only use data available before match kickoff.

For historical/replay mode, it must not use future match results.

Correct:

```text
Use matches where completed_at/kickoff_time < current match kickoff_time
```

Incorrect:

```text
Use full-season table including future matches
```

## Missing Data Strategy

If team has fewer than 5 previous matches:

Option A:

```text
Skip feature generation
```

Option B:

```text
Use available matches and mark low confidence
```

MVP recommendation:

```text
Use available matches if >= 3, otherwise skip.
```

Add warning to decision_logs.

## FeatureBuilder Output

For each eligible match + market + selection:

```text
features row
decision log entry
```
