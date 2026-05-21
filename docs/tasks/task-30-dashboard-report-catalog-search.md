# Task 30 - Dashboard Report Catalog Search

## Goal

Let the dashboard narrow recent comparison reports without changing backend catalog behavior.

## Requirements

- Add a report catalog search control.
- Match query text against report name, filename, league, season, models, and bookmakers.
- Keep recent-first ordering and the current visible result cap.
- Preserve catalog-card report selection behavior.
- Add unit and smoke coverage for the search path.

## Implementation

Status: completed

Added:

```text
dashboard/src/lib/catalog.ts
dashboard/src/lib/catalog.test.ts
```

The catalog helper centralizes filtering, sorting, and limiting. `ReportCatalog` now uses that helper and renders a search input above the report cards.

Smoke coverage now checks:

```text
search by active report name
no-match empty state
clear search and select a catalog card
```

## Verification

Passed before docs-only updates:

```powershell
cd dashboard
npm run test
npm run lint
```

Full verification is still required after this task's docs are saved:

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
dashboard analytical drill-down panel
report-registry timestamps instead of filesystem modified time
replay-analysis improvements
data-provider robustness
```

## Blockers

None.

## Technical Debt

No new documented technical debt.
