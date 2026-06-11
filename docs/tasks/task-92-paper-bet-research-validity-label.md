# Task 92 - Paper Bet Research Validity Label

## Goal

Separate paper-bet research eligibility from recommendation safety labels in API and dashboard surfaces.

## Why

Task 90 intentionally allows positive-EV low-confidence candidates into the paper ledger so the system can learn from real outcomes. The post-deploy Railway cycle created a new paper bet, but the API still labels it `is_valid_open=false` because it carries the `low_confidence` risk flag.

That label is now semantically misleading. Low-confidence paper samples are not actionable recommendations, but they can be valid research records.

## Scope

- Keep low-confidence recommendations blocked from actionable daily decisions.
- Expose a distinct paper-bet research/sample status for ledger records.
- Rename or supplement `is_valid_open` so dashboard/API users can tell the difference between:
  - invalid or unsafe paper-bet records,
  - valid research samples,
  - actionable recommendation-grade candidates.
- Preserve backward compatibility where practical.
- Keep all behavior paper-only.

## Acceptance Criteria

- A low-confidence positive-EV paper bet created for research is not shown as an invalid ledger error.
- Dashboard copy and API fields do not imply that allowed research samples are broken.
- Actionable recommendation gates still reject low-confidence rows.
- Tests cover low-confidence research samples, invalid odds records, and actionable rows separately.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_dashboard_api.py tests/unit/test_paper_bet_logger.py tests/unit/test_recommendation_quality_service.py -q
cd dashboard
npm run test
npm run smoke
```
