# Task 37 - Dashboard Generated Timestamp Ordering

## Goal

Make dashboard report ordering more reproducible by preferring the report's generated timestamp over local filesystem modified time.

## Requirements

- Use `metadata.generated_at` for comparison summary `modified_at` when it is present and valid.
- Keep filesystem modified time as a fallback for older reports.
- Preserve existing dashboard catalog and cross-report behavior.
- Add backend unit coverage for the timestamp preference.

## Implementation

Status: completed

Updated:

```text
app/api.py
tests/unit/test_dashboard_api.py
```

`GET /api/reports/comparisons` now emits `modified_at` from `metadata.generated_at` when the value parses as an ISO timestamp. Older or malformed reports still use the JSON file's filesystem modified time.

Because the dashboard already sorts catalog and recent cross-report data by `modified_at`, no frontend code change was needed.

## Verification

Passed:

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

Potential next phases:

```text
dashboard report metadata refinement
data-provider robustness
replay-analysis improvements
```

## Blockers

None.

## Technical Debt

No new documented technical debt.
