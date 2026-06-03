# Task 72 - Raw Versus Calibrated Recommendation Confidence

Status: completed

Completed: 2026-06-03

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

Completed verification:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_recommendation_service.py tests/unit/test_ai_analysis_service.py tests/unit/test_dashboard_api.py
.\.venv\Scripts\python.exe -m pytest tests/unit/test_recommendation_service.py tests/unit/test_ai_analysis_service.py tests/unit/test_dashboard_api.py tests/unit/test_database.py tests/unit/test_recommendation_quality_service.py
.\.venv\Scripts\python.exe -m ruff check app tests
cd dashboard
npm run test -- --run
npm run lint
npm run build
```

## Result

- Added `model_confidence_score`, `recommendation_confidence_score`, and `confidence_adjustment_reason` to paper recommendations with an additive `009` migration.
- Kept legacy `confidence_score` as the recommendation-level score for compatibility.
- Recommendation generation now preserves raw model confidence and records `high_ev_confidence_calibration` when high-EV cold-start confidence is lifted.
- Live recommendation and recommendation-quality API payloads expose raw, recommendation, and adjustment fields.
- AI recommendation review stores the confidence audit fields in its input and flags calibrated recommendations for cautious review.
- Dashboard filtering uses recommendation confidence and the recommendation table exposes raw-to-recommendation confidence details.

## Next

Task 73 - Confidence Calibration Backtest Scenarios.

## Blockers

This task should follow Task 71 or at least coordinate with its report shape so cycle diagnostics and row diagnostics use the same terminology.

## Technical Debt

Resolved by this task. New rows preserve raw model confidence separately from recommendation confidence while old `confidence_score` remains a compatibility alias for recommendation confidence.
