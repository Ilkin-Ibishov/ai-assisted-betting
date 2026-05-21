# Technical Debt Register

Track known technical debt here so it survives context resets and future agent handoffs.

## Status Values

```text
open
accepted
resolved
```

## Priority Values

```text
P1 - blocks correctness or likely breaks future work
P2 - important maintainability, reliability, or scale issue
P3 - useful cleanup or polish
```

## Open

### P2 - Misli Public Snapshot Depends On Rendered DOM Shape

Status: open  
Introduced: Misli.az public Playwright snapshot prototype  
Area: live provider discovery

`tools/misli-public-snapshot.mjs` reads Misli.az public football rows from rendered DOM classes and maps the first three odds columns to HOME, DRAW, and AWAY when headless rendering hides explicit labels.

Impact:
Misli frontend class or column-order changes can break collection or mislabel odds.

Next:
Task 38 added typed snapshot validation and fail-closed complete 1X2 validation. During Task 40, keep raw row text in stored payloads for audit and continue to treat the DOM-order mapping as provider risk.

### P2 - Misli Bare Time-Only Kickoff Rows Remain Ambiguous

Status: open  
Introduced: Misli.az public Playwright snapshot prototype  
Area: live provider discovery

Task 47 resolves high-confidence relative public labels such as `Bu Gün HH:MM` and `Sabah HH:MM` against snapshot `scraped_at` in the `Asia/Baku` timezone. Some public rows still expose only bare `HH:MM` labels with no full date context.

Impact:
Bare time-only rows cannot be safely scheduled because the date is ambiguous. They are rejected and recorded as live-run errors.

Next:
Keep the fail-closed behavior. If these rows are needed later, derive the date only from a validated public page grouping, allowed detail-page context, or another explicit user-provided snapshot field.

## Recent No-Debt Implementation Notes

Task 22 added a read-only dashboard API without introducing new documented technical debt.

Task 23 added the dashboard scaffold and documented the bundle-size warning that Task 26 later resolved.

Task 24 expanded dashboard analytics and did not introduce new documented technical debt.

Task 25 added repeatable dashboard QA and did not introduce new documented technical debt.

Task 26 resolved the dashboard bundle-size warning.

Task 27 added database identity constraints for older SQLite databases and did not introduce new documented technical debt.

Task 28 added the dashboard report catalog and did not introduce new documented technical debt.

Task 29 filtered pytest-generated reports from the default dashboard catalog and did not introduce new documented technical debt.

Task 30 added frontend report catalog search and did not introduce new documented technical debt.

Task 31 added selected-run drill-down deltas and did not introduce new documented technical debt.

Task 32 added cross-report comparison for the selected run, preserved legacy detail reads when structured analysis is unavailable, and did not introduce new documented technical debt.

Task 33 added a lazy-loaded cross-report ROI trend chart and did not introduce new documented technical debt.

Task 34 added Brier and log-loss calibration lines to the cross-report trend chart and did not introduce new documented technical debt.

Task 35 added trend metric visibility controls and did not introduce new documented technical debt.

Task 36 added selected-run insight classification and did not introduce new documented technical debt.

Task 37 made dashboard report ordering prefer generated comparison timestamps and did not introduce new documented technical debt.

Live paper phase documentation was added for Tasks 38-45 and did not introduce code technical debt. Any fake/manual provider used during implementation must be tracked here if it remains after Task 45.

Task 38 added live provider capability metadata and Misli public snapshot DTO validation. It did not introduce new technical debt beyond the existing Misli DOM/date extraction items above.

Task 39 added the SQLite-backed live run registry and did not introduce new documented technical debt.

Task 40 added manual live collection commands and did not introduce new registry debt. The existing Misli kickoff-date extraction debt remains open because current public snapshots are rejected with structured live-run errors.

Task 41 added the live paper cycle orchestrator. It introduced the P3 run-scoping debt documented above.

Task 42 added manual result collection and settlement reuse. It did not introduce new code debt, but provider-native result discovery remains future work.

Task 43 added the read-only live process status API and did not introduce new documented technical debt. The MVP settlement signal is open versus settled paper-bet counts; expand it during Task 44 only if the dashboard needs more granularity.

Task 44 added the read-only dashboard process monitor and did not introduce new documented technical debt. Smoke requires the local SQLite database to have current migrations; run `init-db` if the dev database predates Task 39.

Task 45 proved the deterministic end-to-end dry run. It did not introduce new code debt, but it reaffirmed two open debts: real Misli kickoff date extraction is still incomplete, and live cycle run scoping must be resolved before scheduling.

Task 46 resolved live cycle run scoping by passing snapshot match ids into scoped feature, prediction, and paper-bet stages. It did not introduce new documented technical debt.

Task 47 narrowed Misli kickoff-date debt by resolving `Bu Gün` and `Sabah` labels. It did not introduce new code debt. Bare time-only rows remain documented as open provider ambiguity.

Task 48 added the deterministic AI backbone slice, provider/prompt/eval contracts, and comparison-report analyst mode. Task 52 added provider-health analyst mode. Remaining AI debt: optional LLM provider integration, richer experiment planner, and deployment-readiness analyst mode are still needed before product-complete AI assistance.

Task 52 added deterministic provider-health AI analysis over recent `live_runs`. It did not introduce new documented technical debt.

Task 49 added Railway/Postgres readiness, `/api/health`, dashboard deployed API base configuration, and dialect-aware migration bookkeeping. It did not introduce new unresolved technical debt. Legacy patch migrations remain intentionally SQLite-only for old local databases; fresh Postgres staging databases use model-managed schema creation.

## Resolved

### P3 - Dashboard Bundle Was Above Vite Warning Threshold

Status: resolved  
Introduced: Task 23 - Dashboard Scaffold  
Resolved by: Task 26 - Dashboard Bundle Optimization  
Area: dashboard frontend

`npm run build` succeeded, but Vite warned that the generated JavaScript chunk was larger than 500 kB after minification.

Resolution:
Moved the Recharts-backed metric chart surface into a lazy-loaded component. Build output now splits into a main app chunk around 321 kB and a chart chunk around 342 kB, so the Vite warning is gone without raising the warning threshold.

### P3 - Dashboard Charts Emitted Recharts Container Warnings

Status: resolved  
Introduced: Task 24 - Analytical Dashboard V1  
Resolved by: Task 25 - Dashboard QA  
Area: dashboard frontend

The first repeatable browser smoke run caught Recharts warnings where charts briefly measured at `-1` width and height during initial render.

Resolution:
Replaced `ResponsiveContainer` usage with a measured chart container and render the chart only after a positive width is available.

### P1 - Old Databases Missing Elo Feature Columns

Status: resolved  
Introduced: Task 09 - Elo Prediction Engine  
Resolved by: Task 10 - Lightweight Schema Migrations  
Area: database schema

Older SQLite databases created before Elo did not have `features.home_elo_rating` or `features.away_elo_rating`.

Resolution:
Added lightweight schema migrations and migration `001_add_feature_elo_columns`.

### P2 - Evaluation Reports Did Not Record Full Model Configuration

Status: resolved  
Introduced: Task 11 - Elo Parameter Configuration  
Resolved by: Task 15 - Record Model Configuration In Reports  
Area: evaluation reports

Evaluation and comparison summaries recorded model name but not full model configuration, such as Elo initial rating, K-factor, and home advantage.

Resolution:
Add model configuration metadata to `evaluation_runs.report_json`, replay summary JSON, and comparison JSON.

### P2 - Comparison SQLite Cleanup Was Best-Effort On Windows

Status: resolved  
Introduced: Task 14 - Comparison Source Cache  
Resolved by: Task 17 - Comparison Temporary Run Databases  
Area: comparison service

SQLite files could remain briefly locked on Windows after a replay run, making project-local scratch DB cleanup best-effort.

Resolution:
Default comparison runs now place scratch SQLite files in an OS temporary directory and retain only `source.csv` in `data/comparisons/<report-name>/`. `--keep-run-dbs` preserves per-run SQLite files under the comparison directory when explicit debugging/audit access is needed. `init_db` also disposes its internal setup engine after migrations.

### P2 - Comparison Runs Were Sequential

Status: resolved  
Introduced: Task 12 - Replay Comparison Command  
Resolved by: Task 18 - Comparison Parallel Execution  
Area: comparison service

`compare-replays` ran each model/bookmaker combination sequentially, which could be slow for larger comparison grids.

Resolution:
Comparison jobs now run through a bounded thread pool while preserving deterministic report order and isolated run databases. Comparison JSON records `parallel_workers`.

### P3 - Model Selection Was Replay-Oriented

Status: resolved  
Introduced: Task 09 - Elo Prediction Engine  
Resolved by: Task 19 - Staged Model Selection  
Area: CLI and prediction service

`--model` was supported by replay workflows, but command-by-command prediction generation and paper-bet selection depended on environment configuration.

Resolution:
Added `--model` to `generate-predictions` and `write-paper-bets` so staged workflows can switch between `baseline_heuristic` and `elo` without changing `MODEL_NAME`.

### P3 - Comparison Parallel Worker Count Was Fixed

Status: resolved  
Introduced: Task 18 - Comparison Parallel Execution  
Resolved by: Task 20 - Configurable Comparison Workers  
Area: comparison service

`compare-replays` used an internal worker cap of 4. This was safe, but larger or constrained workloads needed explicit tuning.

Resolution:
Added `--workers` to `compare-replays`, with CLI and service validation. Comparison JSON continues to record the actual `parallel_workers` used.

### P3 - Live Paper Cycle Processes All Scheduled Matches

Status: resolved  
Introduced: Task 41 - Live Paper Cycle Orchestrator  
Resolved by: Task 46 - Live Cycle Run Scoping  
Area: live orchestration

`run-live-paper-cycle` previously reused broad prediction service methods, which operated on all scheduled matches and all matching feature rows in the database.

Resolution:
Task 46 added scoped prediction service helpers and made `run-live-paper-cycle` resolve match ids from the requested snapshot before generating features, predictions, and paper bets. Mixed databases now leave unrelated scheduled matches untouched.
