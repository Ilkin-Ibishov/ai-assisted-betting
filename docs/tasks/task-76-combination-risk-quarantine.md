# Task 76 - Combination Risk Quarantine

Status: completed

## Goal

Keep combinations/parlays visibly experimental until singles are validated and correlation risk is modeled more responsibly.

## Requirements

- Add a feature flag or risk mode that can keep combinations out of the primary daily decision surface.
- Label combinations as experimental in API, AI review, and dashboard.
- Add exposure checks for duplicate teams, same match, same league, correlated markets, and high leg count.
- Require stronger evidence before any combination is considered actionable.
- Backtest singles and combinations separately in every recommendation calibration report.

## Acceptance Criteria

- Dashboard primary daily card is driven by singles unless combination validation is explicitly enabled.
- AI review can reject combinations without rejecting the existence of single paper candidates.
- Combination rows carry explicit correlation and exposure risk flags.
- Tests cover same-match, duplicate-team, high-leg, and valid independent-leg cases.

## Implementation Notes

- Do not remove the combination engine; quarantine its decision weight.
- Keep combination reports useful for research, but not for primary candidate readiness.
- Prefer conservative defaults.
- Added `experimental_combination`, same-match, duplicate-team, same-league, correlated-market, high-leg, and negative-EV risk flags.
- API and AI review now expose combination decision weight / quarantine counts.
- Dashboard actionable filtering remains singles-driven; experimental combinations stay visible in the research list.
- Recommendation backtests now include a `combination_quarantine` section alongside separate singles and combinations metrics.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_combination_service.py tests/unit/test_ai_analysis_service.py tests/unit/test_recommendation_backtest_service.py tests/unit/test_dashboard_api.py -q
.\.venv\Scripts\python.exe -m ruff check app tests
cd dashboard
npm run test
npm run lint
npm run build
```

## Next

Task 77 - Outcome Learning And Threshold Review Loop.

## Blockers

No blocker for quarantine. Deeper correlation modeling requires more historical and settled recommendation data.

## Technical Debt

Combination quarantine is implemented. Current combination risk remains heuristic and does not model true dependency, bankroll exposure, drawdown, or leg correlation deeply enough for trusted decision support.
