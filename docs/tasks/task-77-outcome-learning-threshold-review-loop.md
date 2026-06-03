# Task 77 - Outcome Learning And Threshold Review Loop

Status: planned

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

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_recommendation_backtest_service.py tests/unit/test_ai_analysis_service.py
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

The current system records outcomes and can backtest, but it does not yet turn those results into a recurring threshold review.
