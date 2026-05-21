# 12 — Testing Strategy

## Test Philosophy

The system must be tested like a financial simulation engine.

Wrong settlement, wrong odds mapping, or wrong timestamps make results useless.

## Unit Tests

### Probability Utilities

Test:

```text
decimal odds -> implied probability
market margin
normalized probabilities
expected value
```

### FeatureBuilder

Test:

```text
last 5 matches only
no future leakage
missing data behavior
correct form points
correct goal averages
```

### PredictionEngine

Test:

```text
probability output within range
edge calculation
confidence score
deterministic output
```

### ValueDetector

Test:

```text
BET when edge high enough
SKIP when edge too low
SKIP when odds too low
SKIP when odds too high
```

### PaperBetLogger

Test:

```text
creates paper bet once
does not duplicate bet
stores stake and EV
```

### ResultSettler

Test:

```text
HOME win
DRAW win
AWAY win
OVER_2_5 win
UNDER_2_5 win
lost bet
void bet
profit calculation
```

### Evaluator

Test:

```text
ROI calculation
hit rate
average odds
Brier score
log loss
bucket breakdown
```

## Integration Tests

### Full Sample Flow

Test command sequence:

```text
init-db
import-sample-data
generate-features
generate-predictions
write-paper-bets
settle-sample-results
evaluate
```

Expected:

```text
paper bets created
bets settled
evaluation run created
```

## No Network Calls in Tests

All tests must run offline.

Use SampleProvider or fixtures.

## Test Data

Create small deterministic fixtures:

```text
Team A vs Team B
Team C vs Team D
completed historical matches
known odds
known results
```

## CI Later

Future GitHub Actions:

```text
pytest
ruff
mypy optional
```

Do not add CI until local tests exist.
