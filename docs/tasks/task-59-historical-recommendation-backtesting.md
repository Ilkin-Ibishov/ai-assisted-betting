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

Task 60 - Railway Worker Deployment And Monitoring.

## Blockers

Requires Task 55 and enough stored paper recommendations to evaluate.

## Technical Debt

Document any mismatch between historical bookmaker fields and live Misli fields.
