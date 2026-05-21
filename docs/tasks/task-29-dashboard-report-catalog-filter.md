# Task 29 - Dashboard Report Catalog Filter

## Goal

Keep pytest-generated comparison reports out of the default dashboard catalog while preserving a debug path to inspect them.

## Requirements

- Hide `pytest_*_comparison.json` reports from `GET /api/reports/comparisons` by default.
- Add an explicit API flag to include test reports when needed.
- Keep existing detail endpoints unchanged.
- Ensure dashboard smoke checks fail if test reports appear in the default catalog.

## Implementation

Status: completed

Added query parameter:

```text
GET /api/reports/comparisons?include_test_reports=true
```

Default behavior:

```text
GET /api/reports/comparisons
```

returns only product/user comparison reports and excludes comparison names that start with `pytest_`.

Smoke behavior:

```text
npm run smoke
```

now fails if any default comparison summary starts with `pytest_`.

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
dashboard report search/filter controls
report-registry timestamps instead of filesystem modified time
replay-analysis improvements
data-provider robustness
```

## Notes

This filter only applies to the list endpoint. Direct detail access to a known `pytest_*` report is intentionally unchanged for debugging and tests.
