# Task 77 - Outcome Learning And Threshold Review Loop

Status: completed

## Goal

Close the paper-learning loop by turning settled outcomes into threshold and calibration recommendations.

## Requirements

- Periodically evaluate settled paper recommendations against the thresholds that created them.
- Track calibration drift over time for raw model confidence and recommendation confidence.
- Recommend threshold changes only when sample size and metrics justify them.
- Produce a conservative "keep, tighten, loosen, or disable" recommendation for:
  - minimum edge
  - minimum expected value
  - confidence floor
  - odds cap
  - combination enablement
- Keep all changes advisory unless a human explicitly applies them.

## Acceptance Criteria

- The system can explain whether recent outcomes support current thresholds.
- Recommendations are sample-size aware and fail closed when evidence is weak.
- Threshold advice is recorded and visible in the dashboard or journal.
- Tests cover small sample, negative ROI, improved calibration, and conflicting metrics.

## Implementation Notes

- Build from recommendation backtests and daily journal entries.
- Do not auto-change production environment variables or strategy settings.
- Treat threshold advice as experiment design, not execution.
- Added structured `threshold_advice` to recommendation backtest reports.
- Added sample-size-aware decisions for minimum edge, minimum expected value, confidence floor, odds cap, and combination enablement.
- AI recommendation backtest summaries now carry threshold advice and advisory next actions.
- Daily paper journals and the dashboard journal summary now surface the latest threshold review.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_recommendation_backtest_service.py tests/unit/test_ai_analysis_service.py tests/unit/test_daily_paper_journal_service.py tests/unit/test_dashboard_api.py -q
.\.venv\Scripts\python.exe -m ruff check app tests
cd dashboard
npm run test
npm run lint
npm run build
```

## Next

After this task, review whether the system is ready for richer model experiments or still needs data-provider hardening.

## Blockers

Requires a meaningful number of settled paper recommendations. The task can ship the framework before the sample is large, but its recommendations must remain conservative.

## Technical Debt

The system now records conservative threshold advice from backtests and carries it into the daily journal. Larger settled samples are still required before any threshold changes should be applied by a human.
