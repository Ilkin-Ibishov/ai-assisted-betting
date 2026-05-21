# Paper Odds Lab

Paper Odds Lab is an offline-first football paper betting research engine.

The first milestone is a local CLI demo that imports deterministic sample data, writes fake paper bets only, settles them, and evaluates the results.

## MVP Commands

```bash
python -m app.cli init-db
python -m app.cli import-sample-data
python -m app.cli generate-features
python -m app.cli generate-predictions
python -m app.cli write-paper-bets
python -m app.cli settle-results
python -m app.cli evaluate
```

## Local Setup

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m app.cli --help
pytest
```

## Dashboard Direction

The next product phase is a local analytical dashboard for tracking replay processes and results.

Accepted stack:

```text
Frontend: React + TypeScript + Vite
UI: shadcn/ui + Tailwind CSS
Charts: Recharts
Tables: TanStack Table
Data fetching/state: TanStack Query
API layer: FastAPI
```

The dashboard should remain local-first, read-only in its first version, and backed by existing SQLite/report artifacts.

Local dashboard commands:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.api:api --reload
cd dashboard
npm run dev -- --host 127.0.0.1 --port 5173
```

Dashboard checks:

```powershell
cd dashboard
npm run test
npm run lint
npm run build
npm run smoke
```

The chart-heavy dashboard module is lazy-loaded so the production build stays below Vite's default chunk-size warning threshold.

The dashboard includes a local report catalog backed by `GET /api/reports/comparisons`, including headline ROI, Brier, settled-bet, sample-size, and modified-time summary fields.

Comparison summary `modified_at` prefers the report's `metadata.generated_at` timestamp and falls back to filesystem modified time for older reports.

The report catalog can be searched locally by report name, filename, league, season, model, or bookmaker.

The run detail panel compares the selected model/bookmaker run against report averages for ROI, Brier score, log loss, and settled bets.

The dashboard also tracks the selected model/bookmaker pair across recent reports in a cross-report comparison table.

The cross-report panel includes a lazy-loaded ROI and calibration trend chart for a fast visual read on selected-run movement over recent reports. ROI, Brier, and log-loss trend lines can be toggled independently.

The selected-run insight panel classifies recent history as strong, noisy, or weak using ROI, latest calibration, and settled sample size.

Older comparison reports can still be opened if structured analysis cannot be derived; the detail API returns `analysis_error` while preserving metadata and runs for dashboard use.

By default, the report catalog excludes `pytest_*` comparison artifacts. Use `GET /api/reports/comparisons?include_test_reports=true` when debugging test-generated reports.

## Next Phase

The next major phase is a paper-only live loop. The roadmap starts at:

```text
docs/specs/live-paper-loop.md
docs/tasks/task-39-live-run-registry.md
```

Task 38 has added the live provider contract and Misli public snapshot DTO validation. Task 39 has added the SQLite-backed live run registry. Task 40 has added manual live collection commands. Task 41 has added the live paper cycle command. Task 42 has added manual result collection and settlement reuse. The remaining implementation order is Tasks 43-45:

```text
process status API
dashboard process monitor
end-to-end dry run
```

Misli.az is the first localized provider candidate for discovery, scoped to public unauthenticated data only. If its usable odds require protected or disallowed paths, the live phase should proceed with a deterministic fake/manual provider first.

Current public discovery artifact:

```powershell
node tools\misli-public-snapshot.mjs --out data\misli-public-snapshot.sample.json
```

This prototype reads public rendered football rows and emits JSON only. Importing it into SQLite belongs to Task 40 after kickoff datetime handling is formalized.

## Safety Boundary

This project is paper betting only. Do not implement real-money betting, bookmaker account automation, CAPTCHA bypass, Cloudflare bypass, stealth browser automation, proxy evasion, or protected scraping.

For agent instructions, start with [AGENTS.md](AGENTS.md).
