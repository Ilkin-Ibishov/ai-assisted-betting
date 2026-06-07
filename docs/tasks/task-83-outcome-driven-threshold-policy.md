# Task 83 - Outcome-Driven Threshold Policy

Status: completed

## Goal

Turn settled recommendation outcomes into a controlled threshold policy instead of leaving threshold advice only as a report.

Task 77 made threshold advice visible and conservative. This task should add an auditable policy layer that can decide whether threshold changes are eligible, proposed, approved, or applied. The default posture must remain fail-closed and paper-only.

## Requirements

- Persist threshold policy proposals with source backtest ids, sample size, ROI, hit rate, Brier score, log loss, drawdown, and rationale.
- Require a minimum settled sample before any change can move beyond advisory state.
- Keep automatic loosening disabled by default.
- Allow automatic tightening or disablement only when evidence is strong, documented, and behind explicit configuration.
- Keep all policy changes auditable through decision logs, AI analysis records, and daily journals.
- Expose latest policy state through CLI and read-only API.
- Show latest policy state in the dashboard daily decision area.
- Preserve current static environment defaults unless a policy is explicitly approved or applied.
- Include rollback information for any applied threshold policy.

## Acceptance Criteria

- Small samples produce `fail_closed` proposals and do not change active thresholds.
- Negative ROI with adequate sample can propose tightening.
- Positive but poorly calibrated outcomes do not loosen thresholds.
- Conflicting ROI and calibration metrics keep thresholds unchanged.
- Applied policy state is visible in the journal and behavior monitor.
- Tests cover small sample, negative ROI, conflicting metrics, approved apply, rollback, and disabled automation.

## Implementation Notes

- Added durable `threshold_policy_runs` state with advisory, proposed, approved, applied, and rolled-back policy records.
- Added `ThresholdPolicyService` to convert the latest recommendation backtest AI threshold review into an auditable policy record.
- Small settled samples remain `advisory` / `fail_closed` and do not change active recommendation thresholds.
- Adequate negative ROI can create a `proposed` tightening policy, but it is not active until explicitly approved and applied.
- Loosening remains advisory by default, including when ROI and calibration metrics conflict.
- Active applied policy values are read by `RecommendationService`; no applied policy means the existing static settings behavior is preserved.
- Scheduled worker runs now evaluate threshold policy after the threshold review and before the daily journal, so the journal captures the latest policy state.
- Added CLI commands:
  - `threshold-policy-evaluate`
  - `threshold-policy-latest`
  - `threshold-policy-approve`
  - `threshold-policy-apply`
  - `threshold-policy-rollback`
- Added read-only API endpoint `GET /api/live/threshold-policy/latest`.
- Added daily journal and production behavior monitor policy visibility.
- Added dashboard visibility in the daily decision/journal area and loop behavior panel.

## Verification

Fresh verification must pass before final handoff:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
cd dashboard
npm run test
npm run lint
npm run build
```

## Suggested Implementation Notes

- Add a `threshold_policy_runs` or equivalent table only if existing `ai_analysis_runs` is not sufficient for durable active policy state.
- Treat `MIN_EDGE`, `MIN_ODDS`, `MAX_ODDS`, confidence floors, and odds caps as policy-controlled values, but preserve config compatibility.
- Prefer a two-stage state machine:
  - `proposed`
  - `approved`
  - `applied`
  - `rejected`
  - `rolled_back`
- Keep the first version human-approved by default. Automatic tightening can be a later feature flag.

## Suggested Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_recommendation_backtest_service.py tests/unit/test_daily_paper_journal_service.py tests/unit/test_dashboard_api.py -q
.\.venv\Scripts\python.exe -m ruff check app tests
cd dashboard
npm run test
npm run lint
npm run build
```

## Next

Task 84 - External Football Context Source Selection.

## Blockers

- Meaningful active threshold changes still require enough settled paper recommendations. The policy layer enforces at least 300 settled single recommendations before a change can move beyond advisory state.

## Technical Debt

No new code debt is intentionally introduced. The remaining product limitation is data quality: without richer permitted football context, applied threshold tightening can only make the odds-first recommendation layer more conservative, not smarter.
