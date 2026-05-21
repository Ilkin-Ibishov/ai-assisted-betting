# Task 26 - Dashboard Bundle Optimization

## Goal

Resolve the open dashboard bundle-size technical debt before the analytical UI grows further.

## Requirements

- Reduce or intentionally split the dashboard JavaScript bundle that currently triggers Vite's 500 kB warning.
- Prefer lazy-loading chart-heavy code if it keeps the first dashboard render lighter.
- Keep the dashboard behavior unchanged.
- Preserve existing dashboard tests and smoke checks.

## Acceptance

`npm run build` completes without the current bundle-size warning, or the warning threshold is adjusted only with a documented reason and measured bundle evidence.

## Implementation

Status: completed

Moved the Recharts-backed metric chart surface out of `App.tsx` into a lazy-loaded component:

```text
dashboard/src/components/dashboard/metric-chart.tsx
```

`App.tsx` now loads the chart module with `React.lazy` and a chart-grid skeleton fallback. Dashboard behavior and rendered chart output are unchanged.

Measured build output after optimization:

```text
dist/assets/index-CrT8ITM0.js         321.11 kB gzip: 97.16 kB
dist/assets/metric-chart-BAxK5SJ-.js  341.93 kB gzip: 99.70 kB
```

The Vite 500 kB chunk-size warning is gone without raising the warning threshold.

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

Browser smoke screenshots were generated for desktop and mobile by `npm run smoke`.

## Next

Continue with the next implementation phase only after choosing the next product surface. Keep using `npm run smoke` after dashboard-facing changes.

## Notes

This task should not add new dashboard features. It is a technical debt phase.
