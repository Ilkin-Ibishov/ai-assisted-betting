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

### P1 - Release Proof Can Confuse Pushed Branch With Production Code

Status: open
Introduced: Post Task 83/84 deployment audit on 2026-06-08
Area: release process and Railway operations
Owner: Task 85 - Direct Main Deployment Proof

Task 83/84 code was pushed to a feature branch and verified locally, but Railway production still served the previous `main` commit. Production health checks were valid for the old release, not for the new implementation.

Impact:
The team can accidentally claim production success for code that has not deployed.

Next:
Use direct `main` pushes for this solo-coder workflow and verify Railway deployment metadata matches the pushed commit before production smoke is counted as release proof.

### P2 - External Context Matching Is Exact-Name Heavy

Status: open
Introduced: Task 84 - External Football Context Source Selection
Area: feature enrichment and source provenance
Owner: Task 86 - Team Alias Coverage For External Context

Task 84 labels Football-Data CSV context when completed history is available, but Misli public team names can differ from Football-Data names. Exact-name matching limits coverage and can make external-context backtests underpowered.

Impact:
External context may look weaker than it is because rows fail to match, or coverage may be uneven across leagues.

Next:
Add deterministic, auditable team aliases with ambiguity handling and coverage reporting before using external-context evidence to approve active threshold policy changes.

### P2 - Threshold Policy Has Mechanism Before Full Governance

Status: open
Introduced: Task 83 - Outcome-Driven Threshold Policy
Area: strategy governance
Owner: Task 87 - Threshold Policy Governance And Decision Log

Task 83 added durable policy states and CLI/API control, but the approval rules are still implicit. The system needs explicit sample-size gates, decision reasons, actor metadata, and evidence links before active policy changes become routine.

Impact:
An operator could apply a policy for the right reason, but the future audit trail would be weaker than the business requirement implies.

Next:
Define governance rules and durable decision logs before adding dashboard mutating controls.

### P2 - Dashboard Policy Controls Are Read-Only

Status: open
Introduced: Task 83 - Outcome-Driven Threshold Policy
Area: dashboard operations
Owner: Task 88 - Dashboard Threshold Policy Operations

The dashboard shows threshold policy state, but approve/apply/rollback remain CLI-only. This is acceptable while governance is incomplete, but it is not ideal for daily operation.

Impact:
Operational changes require shell access and can be harder to review from the same surface that shows journal and behavior evidence.

Next:
After Task 87, add guarded dashboard controls with reason capture and tests for disabled/low-sample states.

### P3 - Odds Movement Uses Computed Summaries Instead Of A Dedicated Table

Status: accepted  
Introduced: Task 54 - Live Odds Movement Tracking  
Area: live odds movement
Owner: future monitoring/data-volume task

Task 54 computes odds movement directly from `odds_snapshots` instead of storing a dedicated movement table.

Impact:
This keeps MVP state simple and auditable, but movement queries may become slower after high-frequency deployed collection.

Next:
Keep computed summaries while data volume is small. If deployed collection makes `/api/live/odds-movement` slow, add a materialized summary table or cached view during monitoring/backtesting work.

### P2 - Recommendation Risk Model Uses Simplified Unit-Stake EV

Status: accepted  
Introduced: Task 55 - Paper Bet Recommendation Engine  
Area: recommendation risk model
Owner: future recommendation-risk/backtesting task

Task 55 computes expected value from model probability and current odds with fixed unit-stake arithmetic. It does not yet include bankroll sizing, exposure caps, market correlation, drawdown controls, or portfolio-level risk.

Impact:
Single recommendation grades are useful for paper analysis, but they are not enough for disciplined combination construction or bankroll-aware strategy.

Next:
Task 56 must add combination and exposure rules. Task 59 should backtest recommendation thresholds and risk assumptions.

### P2 - Threshold Advice Is Not Active Policy

Status: resolved
Introduced: Task 77 - Outcome Learning And Threshold Review Loop
Resolved: Task 83 - Outcome-Driven Threshold Policy
Area: recommendation learning loop
Owner: completed

Task 77 creates conservative threshold advice from settled recommendation backtests and surfaces it through AI summaries, daily journals, and the dashboard. Task 83 adds durable `threshold_policy_runs`, advisory/proposed/approved/applied/rolled-back states, explicit approve/apply/rollback CLI commands, API visibility, journal visibility, behavior visibility, dashboard visibility, and active-policy recommendation gating.

Impact:
Resolved. The system can now turn settled-outcome threshold evidence into auditable strategy configuration while preserving fail-closed paper-only behavior.

Next:
Continue collecting enough settled paper recommendations before approving active changes. Task 84 should improve the upstream probability context so policy changes do not only tighten an odds-first model.

### P2 - Combination Correlation Rules Are Heuristic

Status: accepted  
Introduced: Task 56 - Paper Bet Combination Engine  
Area: paper combination risk model
Owner: future combination-risk/backtesting task

Task 56 rejects duplicate event exposure and filters unsafe legs, but it does not yet model deeper market correlation, league/team exposure concentration, bankroll sizing, drawdown risk, or historical parlay calibration.

Impact:
Ranked combinations are useful for paper-only analysis and dashboard review, but the risk model is still too simple for strategy confidence.

Next:
Task 57 should have AI review call out correlation and confidence limitations. Task 59 should backtest singles versus combinations and calibrate or replace the heuristic rules.

### Planning Note - Live Misli Recommendation Roadmap

Status: accepted  
Introduced: Task roadmap generation for Tasks 53-62  
Area: planning
Owner: future roadmap review task

Tasks 53 through 62 have been added to prevent recommendation work from skipping ingestion reliability, odds movement, deterministic scoring, AI safety evals, dashboard visibility, deployment monitoring, and final readiness review.

No new implementation debt was introduced by this planning update. Expected future debt areas to watch are Misli selector drift, correlation heuristics for paper bet combinations before historical validation, Railway worker cadence and cold-start limits, and AI review eval coverage if an LLM-backed provider is enabled.

### P2 - Misli Public Snapshot Depends On Rendered DOM Shape

Status: open  
Introduced: Misli.az public Playwright snapshot prototype  
Area: live provider discovery
Owner: future Misli provider reliability task

`tools/misli-public-snapshot.mjs` reads Misli.az public football rows from rendered DOM classes and maps the first three odds columns to HOME, DRAW, and AWAY when headless rendering hides explicit labels.

Impact:
Misli frontend class or column-order changes can break collection or mislabel odds.

Next:
Task 38 added typed snapshot validation and fail-closed complete 1X2 validation. Task 53 added comma-odds normalization, non-empty identity validation, skipped-row extraction metadata, parser-drift errors for empty snapshots, and low-confidence errors when public rows do not become usable events. Continue to treat DOM-order mapping as provider risk until Task 54+ can validate odds movement against repeated snapshots.

### P2 - Misli Bare Time-Only Kickoff Rows Need Stronger Date Context

Status: accepted
Introduced: Misli.az public Playwright snapshot prototype
Updated by: Task 69 - Misli Bare-Time Resolution
Area: live provider discovery
Owner: future Misli provider reliability task

Task 47 resolves high-confidence relative public labels such as `Bu Gun HH:MM` and `Sabah HH:MM` against snapshot `scraped_at` in the `Asia/Baku` timezone. The first Task 68 production worker proof showed current Misli public pages can also expose bare `HH:MM` rows in the upcoming-event list.

Impact:
Task 69 resolves bare `HH:MM` rows to the snapshot `scraped_at` local date. This is accepted for the upcoming public football list because it unblocks real fresh snapshots while still requiring a trusted scrape timestamp.

Next:
The stronger long-term source of truth remains date group/header extraction from the rendered page, allowed detail-page context, or another explicit user-provided snapshot field.

## Recent No-Debt Implementation Notes

Task 83 added the active threshold policy layer without introducing documented new debt. It intentionally keeps loosening advisory and requires human approval/apply steps before policy changes affect recommendations.

Task 82 reconciled the backlog and proved the deployed production loop on 2026-06-07. It did not introduce new code debt.

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

Task 50 added the one-shot scheduled paper worker and did not introduce new documented technical debt. Worker cadence is intentionally externalized to Railway or another scheduler and remains an open deployment decision, not implementation debt.

Task 53 hardened Misli parsing and provider-health drift reporting. It did not resolve the rendered-DOM selector dependency, which remains open above.

Task 54 added computed odds movement summaries from existing `odds_snapshots`; see the accepted P3 movement-summary tradeoff above.

Task 55 added deterministic paper recommendations; see the accepted P2 simplified unit-stake EV tradeoff above.

Task 56 added paper bet combinations; see the accepted P2 combination-correlation tradeoff above.

Task 57 added deterministic AI review over recommendations and combinations. It did not introduce new implementation debt, but optional LLM-backed recommendation review remains future work and must add provider-specific eval fixtures before enablement.

Task 58 added a direct-rendered recommendation dashboard panel. It did not introduce a current performance issue, but the panel should be revisited for pagination or virtualization if recommendation history grows beyond the API-limited working set.

Task 59 added historical recommendation backtesting, dashboard-compatible companion exports, and deterministic AI backtest summaries. It did not introduce new technical debt. Existing recommendation and combination risk-model limitations remain tracked above until larger backtests justify stronger thresholds or richer exposure modeling.

Task 51 added a Railway deployment runbook and `production-smoke` command. It did not introduce new implementation debt. First deployed smoke evidence still requires real Railway staging URLs and credentials, which is an operational prerequisite rather than code debt.

Task 60 added worker freshness monitoring, `/api/live/worker-status`, and production-smoke checks for worker freshness and recommendation endpoint health. It did not introduce new code debt. Railway cron cadence, cold starts, and service-to-service networking remain operational considerations documented in `docs/deployment/railway-readiness.md`.

Task 61 added operational guardrails, `operational-status`, `/api/operations/guardrails`, and a dashboard guardrails panel. It did not introduce new code debt. External alert destinations remain an open product/operations decision in `docs/agent/04_OPEN_QUESTIONS.md`; notification bots are intentionally out of scope until staging use proves the guardrail states.

The 2026-05-28 post-audit fix tightened recommendation safety by rejecting current-odds negative-EV recommendations even when stored prediction edge is positive. It also fixed the recommendation-output guardrail to count recommendation records created during the latest worker run, not only records created after worker completion. No new technical debt was introduced; the broader simplified EV and cold-start input limitations remain tracked above.

Task 62 added the final production readiness review. It did not introduce new code debt. The system is conditionally ready for monitored paper-only Railway staging, with deployed Railway smoke evidence still pending.

Task 63 added Railway API config-as-code through `railway.json` and an explicit Dockerfile. It did not introduce new code debt. Railway agent tooling has been installed locally, but the restarted Codex session still does not expose a dedicated Railway MCP namespace; Railway operations are handled through the linked Railway CLI. The first Railpack config attempt built but crashed at runtime because dependencies such as `typer` were not visible in the runtime image; the Dockerfile is now the deployment source of truth. Commit `ad00259` deployed successfully to `https://ai-assisted-betting-production.up.railway.app`. Railway Postgres has been added and `DATABASE_URL` is set on the API service. The first Postgres-backed deploy exposed a SQLAlchemy driver-default issue: plain Railway `postgresql://...` URLs attempted to load `psycopg2`, so the DB engine now normalizes them to `postgresql+psycopg://...`. CLI database URL output is redacted for safer Railway logs. Commit `e129e8a` is healthy on Railway Postgres. A one-off scheduled paper worker has completed against Railway Postgres and deployed API `production-smoke` passes. Continuous readiness still needs a dedicated Railway scheduled worker service and dashboard service deployment.

Task 64 added Railway dashboard service packaging and configurable API CORS for Railway dashboard origins. It did not introduce new code debt. The dashboard is deployed at `https://dashboard-production-0a69.up.railway.app` and deployed dashboard smoke passes. The dashboard service was deployed with `railway up` because the Railway CLI repo-link creation path returned an OAuth authorization error; future dashboard redeploys can use the same CLI upload path or the user can reconnect the service to GitHub in Railway's UI. Continuous readiness still needs a dedicated scheduled worker service.

Task 65 added `Dockerfile.worker` and a Railway scheduled worker deployment path. It did not introduce code debt. The dedicated `worker` Railway service is deployed and cron-triggered runs work. The worker currently uses the deterministic Task 45 fixture snapshot, which is operationally acceptable for scheduler/database proof but not a substitute for fresh Misli public snapshot collection. Replace the fixture with a safe public/user-provided snapshot generation workflow before treating the worker as live provider coverage.

Task 66 simplified the dashboard into a daily decision card and moved historical model analytics into collapsed diagnostics. It did not introduce new code debt. Existing product debt remains: the scheduled worker still uses deterministic fixture input, and recommendations do not yet consume richer current league, club, player, injury, lineup, or schedule context from external research sources.

Task 67 added `WORKER_SNAPSHOT_URL` / `--snapshot-url` support, so the scheduled worker can consume fresh HTTPS JSON snapshots and refresh recommendations, combinations, and AI review after each successful cycle. It did not introduce new code debt. The deterministic fixture remains as a safe fallback. Remaining product debt: a browser-enabled snapshot producer still needs to create and publish fresh Misli snapshot JSON, and recommendations still do not consume richer current league, club, player, injury, lineup, or schedule context from external research sources.

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

### P1 - Fresh Misli Snapshot Producer Needs Railway Scheduling Proof

Status: resolved
Introduced: Task 68 - Fresh Misli Snapshot Producer
Resolved by: Task 68 Railway wiring
Area: live ingestion and Railway operations

Task 68 added the API latest-snapshot store, token-protected snapshot ingest, producer POST support, and `Dockerfile.snapshot`. Railway now has a scheduled `snapshot-producer` service, API `SNAPSHOT_INGEST_TOKEN`, producer `SNAPSHOT_POST_URL`, and worker `WORKER_SNAPSHOT_URL`.

Resolution:
Created and deployed the `snapshot-producer` Railway service. A one-off producer run posted a fresh 21-event Misli snapshot to `/api/live/snapshots/latest/misli-public`. The remaining production proof shifted to Task 69 because the first worker run consumed the fresh snapshot but failed on a bare `HH:MM` kickoff row.
### P2 - Recommendation Inputs Are Still Odds-First

Status: open
Introduced: Task 68 - Fresh Misli Snapshot Producer
Area: recommendation quality

The fresh Misli producer captures public list-page odds and match metadata. It does not yet enrich recommendations with current league table position, club form, player stats, injuries, lineups, rest days, travel, or schedule congestion.

Resolution target:
Task 84 selected Football-Data CSV and added external-context feature provenance plus backtest grouping. Remaining work is team alias coverage and broader source enrichment before calling the system product-complete for daily decision support.

### P2 - Live Cold-Start Features Use Neutral Team Form

Status: accepted
Introduced: Post-audit live recommendation fix on 2026-05-28
Area: live prediction quality

Fresh Misli snapshots can contain clubs that do not yet have completed-match history in the local database. The live cycle now still creates auditable feature and prediction rows by using neutral team-form and goal values while preserving bookmaker-normalized probabilities and initial Elo ratings.

Impact:
This prevents fresh live cycles from producing only `missing_prediction` recommendation records, but it does not add real team-strength evidence. With current thresholds, cold-start recommendations should remain conservative and typically reject on low edge/confidence until richer inputs exist.

Next:
Treat cold-start predictions as a staging bridge. Replace or enrich them with vetted historical/team/stat sources before relying on the dashboard for stronger daily decision support.

### P1 - Snapshot Producer Railway Upload Stuck In Building

Status: resolved
Introduced: Task 70 - Snapshot Producer Railway Image
Resolved by: Task 70 - Snapshot Producer Railway Image
Area: Railway operations

The latest `snapshot-producer` Railway upload used `Dockerfile.snapshot`, installed Playwright browsers during build, exported an image, but remained as a stopped `BUILDING` deployment without becoming the active successful cron image.

Resolution:
Task 70 switched `Dockerfile.snapshot` to `mcr.microsoft.com/playwright:v1.60.0-noble` so browser dependencies are supplied by the base image. Railway deployment `df944e43-9e2c-4bad-9b1f-0c582f4e5e37` reports `SUCCESS`, the old stopped `BUILDING` deployment was removed, and an immediate producer run posted a fresh 21-event snapshot with `scraped_at=2026-05-28T00:05:28.437Z`.

Follow-up:
The producer image debt is closed. The next operational proof is the scheduled worker consuming that fresh snapshot and refreshing dashboard recommendations.

### P1 - Fresh Misli Snapshot Contains Non-Actionable 1.00 Odds

Status: resolved
Introduced: Task 70 - Snapshot Producer Railway Image
Resolved by: Task 70 - Snapshot Producer Railway Image
Area: live ingestion and provider validation

The first scheduled worker run after the fresh snapshot proof consumed the latest Misli snapshot but failed provider validation on two rows where a primary 1X2 odd was exactly `1.00`. The provider correctly rejects odds at or below 1, but the producer should not post rows that cannot become valid advisory paper-bet inputs.

Resolution:
Task 70 filters producer rows unless HOME, DRAW, and AWAY 1X2 selections are all present and all primary 1X2 odds are greater than 1. The Railway worker run started at `2026-05-28T01:00:33Z` completed with zero errors on the filtered fresh snapshot.

### P2 - Snapshot Producer Logs Full Snapshot Payloads

Status: resolved
Introduced: Task 70 - Snapshot Producer Railway Image
Resolved by: Task 70 - Snapshot Producer Railway Image
Area: Railway operations

The first successful scheduled producer run emitted the full snapshot JSON to Railway logs and hit the Railway per-replica log rate limit.

Resolution:
The producer now writes JSON to stdout only when it is not posting to the API and no `--out` path is provided. Cron producer runs still emit the concise `snapshot_posted=<url>` stderr line.

### P1 - Recommendation Cycles Need One Auditable Quality Report

Status: resolved
Introduced: Post-deployment audit on 2026-06-03
Resolved by: Task 71 - Recommendation Quality Cycle Report
Owner: Task 71 - Recommendation Quality Cycle Report
Area: recommendation quality and observability

Production audits currently require joining worker status, recommendations, combinations, guardrails, AI review, and logs by hand. This makes the system harder to reason about after several cron cycles.

Resolution:
Task 71 added `RecommendationQualityService`, `GET /api/live/recommendation-quality`, a `recommendation-quality` CLI command, and dashboard daily-card cycle quality counts. The report explains actionable, watchlist, rejected, blocked, deduped-fresh, and AI-reviewed states from one surface.

### P1 - Recommendation Confidence Blends Raw Model Signal And Calibration

Status: resolved
Introduced: High-EV confidence calibration on 2026-06-03
Resolved by: Task 72 - Raw Versus Calibrated Recommendation Confidence
Owner: Task 72 - Raw Versus Calibrated Recommendation Confidence
Area: recommendation scoring

The calibrated recommendation score unlocked paper actionable candidates, but the same `confidence_score` field now carries a recommendation-level score rather than the untouched raw model confidence.

Resolution:
Task 72 added nullable confidence-audit columns, preserved raw prediction confidence in `model_confidence_score`, kept `confidence_score` as the compatibility recommendation confidence, exposed `recommendation_confidence_score` and `confidence_adjustment_reason` through API/dashboard surfaces, and made AI recommendation review flag calibrated rows explicitly.

### P1 - High-EV Confidence Calibration Needs Backtest Proof

Status: resolved
Introduced: High-EV confidence calibration on 2026-06-03
Resolved by: Task 73 - Confidence Calibration Backtest Scenarios
Owner: Task 73 - Confidence Calibration Backtest Scenarios
Area: model evaluation

The calibration change improved live paper candidate visibility, but it could still be confidence theater unless settled outcomes and historical backtests show better behavior.

Resolution:
Task 73 added raw-versus-calibrated confidence backtest scenarios with EV thresholds, confidence floors, odds caps, ROI, hit rate, Brier score, log loss, drawdown, settled sample size, edge buckets, odds buckets, confidence buckets, calibrated-candidate counts, and AI backtest guidance that marks calibration as provisional when sample size is small.

### P2 - Team Strength Inputs Are Still Thin

Status: resolved
Introduced: Post-deployment audit on 2026-06-03
Resolved by: Task 74 - Richer Team Strength Feature Inputs
Owner: Task 74 - Richer Team Strength Feature Inputs
Area: prediction quality

The system is operationally stable, but the baseline model still relies heavily on bookmaker probabilities, shallow form, neutral cold-start features, and small heuristic adjustments.

Resolution:
Task 74 added deterministic local feature enrichment tiers, provenance, rest days, goal-difference trend, odds movement velocity, overround-normalized bookmaker probability, and enriched-only prediction adjustments. AI recommendation review now separates odds-only actionable rows from enriched actionable rows.

Remaining source-selection note:
External league table, opponent-adjusted, lineup, injury, and closing-line sources still require stability/legal review before integration.

### P2 - Daily Learning Narrative Is Missing

Status: resolved
Introduced: Post-deployment audit on 2026-06-03
Resolved by: Task 75 - Daily Paper Trading Journal
Owner: Task 75 - Daily Paper Trading Journal
Area: product learning loop

The dashboard shows live facts, but there is not yet a durable daily journal explaining what the system would have picked, what AI rejected, what settled, and what should be learned.

Resolution:
Task 75 added deterministic daily paper-only journal entries that connect recommendations, AI review, paper bets, settled outcomes, recommendation quality state, calibration observations, and traceable source ids. Journal entries are available through CLI, API, and the dashboard daily card.

### P2 - Combinations Are Premature For Primary Decisions

Status: resolved
Introduced: Post-deployment audit on 2026-06-03
Owner: Task 76 - Combination Risk Quarantine
Area: recommendation risk

Combinations are generated and reviewed, but deeper dependency, exposure, and correlation modeling is still not strong enough for primary decision support.

Resolution:
Task 76 keeps combinations experimental, excludes them from actionable daily dashboard decisions, labels API/AI/dashboard combination rows, adds same-match, duplicate-team, same-league, correlated-market, high-leg, and negative-EV risk flags, and adds combination quarantine counts to recommendation backtests. Deeper dependency and bankroll modelling remains future model maturity work, but combinations no longer drive primary candidate readiness.

### P2 - Settled Outcomes Do Not Yet Drive Threshold Review

Status: resolved
Introduced: Post-deployment audit on 2026-06-03
Owner: Task 77 - Outcome Learning And Threshold Review Loop
Area: learning loop

The system records settled paper outcomes and can backtest, but it does not yet turn those results into recurring advice about whether thresholds should be kept, tightened, loosened, or disabled.

Resolution:
Task 77 adds conservative threshold advice to recommendation backtests, propagates it through AI backtest summaries, and surfaces the latest advice in daily paper journals and the dashboard. Advice remains paper-only and advisory; applying threshold changes still requires a human decision and larger settled samples.
