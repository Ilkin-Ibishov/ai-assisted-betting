# Task 73 - Confidence Calibration Backtest Scenarios

Status: completed

## Goal

Prove whether high-EV confidence calibration improves historical paper performance or merely makes weak signals look stronger.

## Requirements

- Add backtest scenarios comparing raw confidence-only grading against calibrated recommendation confidence.
- Include stricter and looser EV thresholds.
- Include odds caps and confidence floors as scenario parameters.
- Report ROI, hit rate, Brier score, log loss, drawdown, settled sample size, edge buckets, odds buckets, and confidence buckets.
- Emit an AI recommendation-backtest analysis that explicitly answers whether calibration should remain enabled.

## Acceptance Criteria

- Backtest output shows old versus calibrated recommendation behavior side by side.
- Calibration is considered useful only if it improves enough metrics on enough settled samples.
- Reports call out small-sample risk instead of overclaiming.
- Tests cover scenario generation and a deterministic case where calibration changes candidate inclusion.

## Implementation Notes

- Build on `RecommendationBacktestService` rather than creating a separate report path.
- Keep scenario names stable so dashboard and AI analysis can compare them across runs.
- Treat ROI as exploratory when sample size is small or calibration metrics disagree.

## Implementation Summary

- Added stable `calibration_scenarios` to recommendation backtest reports.
- Compared `raw_model` confidence against `calibrated_recommendation` confidence across looser, baseline, stricter, and no-odds-cap scenarios.
- Added scenario-level ROI, hit rate, Brier score, log loss, max drawdown, settled sample size, edge buckets, odds buckets, confidence buckets, and calibrated-candidate counts.
- Added `calibration_comparison` deltas for the baseline raw-versus-calibrated scenario.
- Updated deterministic recommendation-backtest AI analysis with `calibration_decision`, small-sample risk flags, and explicit keep/disable guidance.
- Added tests for scenario generation and a deterministic case where calibration changes candidate inclusion.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_recommendation_backtest_service.py tests/unit/test_ai_analysis_service.py
.\.venv\Scripts\python.exe -m ruff check app tests
python -m app.cli backtest-recommendations --help
python -m app.cli analyze-recommendation-backtest --help
```

Verified on 2026-06-04:

- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_recommendation_backtest_service.py tests/unit/test_ai_analysis_service.py -q` - 19 passed.
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_database.py tests/unit/test_recommendation_service.py tests/unit/test_dashboard_api.py tests/unit/test_recommendation_quality_service.py -q` - 72 passed.
- `.\.venv\Scripts\python.exe -m ruff check app tests` - passed.
- `.\.venv\Scripts\python.exe -m app.cli backtest-recommendations --help` - passed.
- `.\.venv\Scripts\python.exe -m app.cli analyze-recommendation-backtest --help` - passed.

## Next

Task 74 - Richer Team Strength Feature Inputs.

## Blockers

Meaningful conclusions require enough settled recommendations. If the sample is too small, this task should still produce the comparison framework and clearly label results as provisional.

## Technical Debt

The comparison framework is now implemented. Meaningful confidence in the decision still depends on accumulating enough settled recommendations; small samples are reported as provisional.
