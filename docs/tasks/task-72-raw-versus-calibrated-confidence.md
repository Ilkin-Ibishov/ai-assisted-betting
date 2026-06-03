# Task 72 - Raw Versus Calibrated Recommendation Confidence

Status: planned

## Goal

Separate raw model confidence from recommendation-level calibrated confidence so the system does not hide confidence inflation inside a single score.

## Requirements

- Preserve the prediction engine's raw confidence score.
- Store and expose a distinct recommendation confidence score used for paper recommendation grading.
- Store and expose a calibration reason when recommendation confidence differs from raw model confidence.
- Update AI recommendation review to mention confidence calibration when it affects actionable rows.
- Update dashboard rows to show calibrated confidence while making the raw-vs-calibrated distinction inspectable.

## Acceptance Criteria

- API consumers can see both raw model confidence and recommendation confidence.
- A calibrated actionable row explains why confidence was lifted.
- Low-confidence watchlist rows remain clearly low confidence.
- Tests prove raw confidence is not overwritten when recommendation confidence is calibrated.

## Implementation Notes

- Prefer additive schema changes or backward-compatible nullable fields.
- Candidate fields:
  - `model_confidence_score`
  - `recommendation_confidence_score`
  - `confidence_adjustment_reason`
- Keep old `confidence_score` behavior stable until the API/dashboard migration is complete.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_recommendation_service.py tests/unit/test_ai_analysis_service.py tests/unit/test_dashboard_api.py
.\.venv\Scripts\python.exe -m ruff check app tests
cd dashboard
npm run test
npm run lint
npm run build
npm run smoke
```

## Next

Task 73 - Confidence Calibration Backtest Scenarios.

## Blockers

This task should follow Task 71 or at least coordinate with its report shape so cycle diagnostics and row diagnostics use the same terminology.

## Technical Debt

The current `confidence_score` on recommendations may be raw or calibrated depending on generation logic. That ambiguity is acceptable for paper staging but should not persist.
