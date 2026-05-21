# 09 — Value Detection and Paper Bets

## Value Definition

A paper bet candidate exists when:

```text
model_probability > bookmaker_probability + safety_margin
```

where:

```text
edge = model_probability - bookmaker_probability
```

## MVP Rule

Initial config:

```text
min_edge = 0.07
min_odds = 1.70
max_odds = 3.50
stake_units = 1.0
```

Paper bet if:

```text
edge >= min_edge
and odds_decimal >= min_odds
and odds_decimal <= max_odds
```

## Expected Value

For a 1 unit stake:

```text
EV = model_probability * (odds_decimal - 1) - (1 - model_probability)
```

Store:

```text
expected_value
```

## Paper Bet Creation Rules

Create a paper bet only if:

```text
prediction.decision == BET
prediction has no existing paper_bet
match is not completed
odds_taken exists
```

## No Real Bet Execution

Never place a real bet.

Never connect to bookmaker bet placement flows.

## Settlement Rules

For 1X2:

```text
HOME wins if home_score > away_score
DRAW wins if home_score == away_score
AWAY wins if away_score > home_score
```

For Over/Under 2.5:

```text
total_goals = home_score + away_score
OVER_2_5 wins if total_goals > 2.5
UNDER_2_5 wins if total_goals < 2.5
```

## Profit/Loss

If won:

```text
profit_loss_units = stake_units * (odds_taken - 1)
```

If lost:

```text
profit_loss_units = -stake_units
```

If void:

```text
profit_loss_units = 0
```

## CLV

Closing Line Value:

```text
clv = closing_odds - odds_taken
```

For a more advanced version, calculate probability-based CLV.

MVP can store decimal difference.

## Why CLV Matters

ROI can be positive due to luck.

CLV shows whether the system generally beats market movement.

If the system often takes better odds than closing odds, it may have a real signal.

## Stake Strategy

MVP:

```text
fixed 1 unit
```

Do not implement:

```text
martingale
loss recovery
progressive staking
aggressive Kelly staking
```

Kelly can be considered much later, only after reliable calibration.
