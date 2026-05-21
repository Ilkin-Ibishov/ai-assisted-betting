# Task 28 - Dashboard Report Catalog

## Goal

Make the dashboard easier to scan across comparison reports before selecting one for deeper analysis.

## Requirements

- Enrich comparison report summaries with headline metrics for catalog display.
- Add a compact report catalog/history surface to the dashboard.
- Allow selecting a report from the catalog.
- Keep existing selector, charts, rankings, and smoke checks working.

## Implementation

Status: completed

API summary fields added to `GET /api/reports/comparisons`:

```text
modified_at
total_settled_bets
best_roi
best_brier_score
best_log_loss
sample_size_smallest
sample_size_largest
```

Dashboard additions:

```text
report catalog panel
recent report cards sorted by modified_at
headline ROI / Brier / settled metrics
clickable catalog cards that select the active report
fallback display for stale or incomplete summary payloads
```

Smoke coverage now checks:

```text
catalog renders
catalog metric values match API summary data
catalog card selection updates the report selector
```

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

Potential next implementation phases:

```text
dashboard report filtering/search
comparison report cleanup to hide pytest artifacts from product catalog
replay-analysis improvements
data-ingestion/provider robustness
```

## Notes

`modified_at` originally came from the comparison JSON file's filesystem modification time. Task 37 changed the summary API to prefer `metadata.generated_at` when present and valid, with filesystem modified time retained as the fallback for older reports.
