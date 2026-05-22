# Task 59 - Historical Recommendation Backtesting

## Goal

Evaluate whether live recommendation and combination rules would have performed well on historical and replayable data.

## Requirements

- Replay recommendation rules against historical Football-Data and any stored Misli paper cycles.
- Report ROI, hit rate, calibration, drawdown, edge buckets, market buckets, and model/provider split.
- Compare singles versus combinations.
- Feed results into AI analysis for experiment review.
- Export reports consumable by the existing dashboard catalog.

## Acceptance Criteria

- Backtest reports show whether recommendation thresholds are too loose or too strict.
- Combination performance is measured separately from single-leg recommendations.
- AI analysis can summarize backtest weaknesses and next experiment ideas.
- Tests cover deterministic report generation and threshold-sensitive ranking changes.

## Implementation Notes

Implemented in Task 59:

- Added `RecommendationBacktestService` to evaluate persisted active recommendations joined to completed matches.
- Reported singles and combinations separately with ROI, hit rate, Brier score, log loss, drawdown, edge buckets, market buckets, model/provider buckets, and threshold-sensitivity scenarios.
- Added `backtest-recommendations` CLI export for CSV plus canonical recommendation-backtest JSON.
- Added a dashboard-compatible `_comparison.json` companion report so the existing report catalog can list backtest outputs.
- Added `analyze-recommendation-backtest` and `recommendation_backtest_summary` AI analysis records over exported backtest JSON.
- Added deterministic advisory risk flags for small samples, negative ROI, combination underperformance, under-sampled combinations, and threshold sensitivity.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
cd dashboard
npm run test
npm run lint
npm run build
npm run smoke
```

## Next

Task 51 - Railway Deployment Runbook And Production Smoke, then Task 60 - Railway Worker Deployment And Monitoring.

## Blockers

No implementation blocker remains. Meaningful conclusions still require enough stored paper recommendations and completed results.

## Technical Debt

Current reports use historical settled recommendations and companion dashboard comparison JSON. Deeper bankroll sizing, exposure caps, and richer combination correlation modeling remain tracked in `docs/agent/05_TECHNICAL_DEBT.md`.
