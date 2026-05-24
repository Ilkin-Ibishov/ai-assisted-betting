# Live Paper Loop

## Purpose

The next major product phase is a local, paper-only live loop that can repeatedly ingest upcoming fixtures and odds, generate predictions, write paper bets, settle completed matches, and expose process status to the dashboard.

This phase must not place real bets, automate bookmaker accounts, bypass protections, or scrape protected pages. It is an operational extension of the existing offline/replay engine.

## Current Starting Point

Already available:

```text
SQLite schema and migrations
sample import
Football-Data CSV import
historical replay
baseline and Elo prediction engines
value detection
paper bet logging
settlement and evaluation
comparison reports
dashboard report analytics
```

Available in the current live phase:

```text
live run registry
process status API
manual Misli public snapshot match/odds collection
manual result collection and settlement reuse
live paper cycle orchestration
scoped live cycle prediction stages
provider error visibility through live_runs
dashboard process monitor
deterministic end-to-end live paper dry run
```

Not yet available:

```text
provider-native result discovery
complete resolution for bare time-only Misli rows
```

Task 50 added a one-shot scheduled paper worker command. It does not run an infinite local loop; Railway or another scheduler owns cadence.

## Phase Goal

Create a reliable local dry-run workflow:

```text
collect upcoming matches
collect current odds snapshots
generate features
generate predictions
write duplicate-safe paper bets
later collect results
settle open paper bets
evaluate and monitor status
```

The loop may be manually invoked first. Scheduling can be added only after the manual flow is deterministic and idempotent.

## Safety Rules

- Paper bets only.
- No real-money execution.
- No bookmaker login automation.
- No CAPTCHA bypass, Cloudflare bypass, stealth browser automation, or proxy evasion.
- Use official, public, permitted, or user-provided data sources.
- If a source is blocked or protected, skip it and record an error.
- Keep provider credentials out of logs and reports.

## First Provider Candidate

The first localized live provider candidate is:

```text
Misli.az
```

Rationale:

```text
localized to Azerbaijan
relevant to the user's market
official local betting brand to evaluate first
```

Boundary:

```text
use public, unauthenticated, allowed pages or endpoints only
do not automate login or account pages
do not scrape disallowed account or live-bet detail paths
do not bypass CAPTCHA, Cloudflare, app protections, rate limits, or bot controls
do not place real bets
```

As of 2026-05-19, `https://www.misli.az/robots.txt` disallows:

```text
/hesabim/*
/uyelik/*
/sayt-parametrleri*
/idman-novleri-canli-merc-detal/*
/paylasilan-kupon/*
/paylasilan-kupon/idman-novleri/*
```

Public discovery found rendered football rows with event names and 1X2 odds on:

```text
https://www.misli.az/idman-novleri/futbol
```

Current prototype:

```text
tools/misli-public-snapshot.mjs
docs/research/misli-public-discovery.md
```

Use Misli as a public snapshot source for Tasks 38-40, subject to validation. If full kickoff datetimes, complete 1X2 odds, or safe public access cannot be validated, use a deterministic fake/manual provider for the end-to-end dry run and record Misli as skipped for the specific reason.

## Architecture

```text
Provider adapter
  -> Raw DTOs
  -> Normalizer
  -> Repository writes
  -> Feature generation
  -> Prediction generation
  -> Value detection
  -> Paper bet logger
  -> Process run registry
  -> Dashboard API
```

Provider adapters must not write directly to the database. They return raw provider DTOs. Existing service/repository layers own normalization and persistence.

## Required New Concepts

### Provider Capability

Each provider should declare:

```text
supports_matches
supports_odds
supports_results
supported_leagues
supported_markets
rate_limit_notes
requires_full_kickoff_datetime
safety_boundary_notes
```

Misli public snapshot capability:

```text
supports_matches: true for rows with full dates or high-confidence relative date labels
supports_odds: true for public 1X2 football snapshot rows
supports_results: false for MVP unless separately validated on public allowed pages
supported_markets: 1X2 first
```

Task 47 resolves `Bu Gün HH:MM` and `Sabah HH:MM` against the snapshot `scraped_at` timestamp in the `Asia/Baku` timezone. Bare `HH:MM` rows without full date context still fail closed.

### Live Run Registry

Every live collection or live paper loop run should record:

```text
run_id
run_type
status
started_at
finished_at
items_read
items_created
items_updated
items_skipped
errors_count
error_summary
provider
league
season
lookahead_hours
model_name
```

Task 39 implemented this as the SQLite-backed `live_runs` table with repository helpers for starting, completing, failing, and reloading runs by `run_id`.

### Live Process Status API

Task 43 implemented read-only FastAPI endpoints over the live run registry and paper bet settlement state:

```text
GET /api/live/status
GET /api/live/runs
GET /api/live/runs/{run_id}
```

The status endpoint exposes latest run, latest successful run, latest failed run, open paper-bet count, settled paper-bet count, total run count, and total live-run errors. These endpoints are the backend contract for Task 44 dashboard monitoring.

### Duplicate Protection

Live commands must be idempotent:

```text
matches: source + source_match_id
odds: match_id + source + bookmaker + market + selection + snapshot_time
features: match_id + market + selection + feature_version
predictions: feature_id + model_name + model_version
paper bets: prediction_id
```

Task 27 already added database identity constraints for the most important existing rules.

## Command Direction

The live phase should add or complete these commands:

```powershell
python -m app.cli collect-matches
python -m app.cli collect-odds
python -m app.cli run-live-paper-cycle
python -m app.cli collect-results
python -m app.cli settle-results
python -m app.cli evaluate
python -m app.cli run-scheduled-paper-worker
```

Task 40 implemented the manual Misli public snapshot forms:

```powershell
python -m app.cli collect-matches --provider misli-public --snapshot data\misli-public-snapshot.sample.json
python -m app.cli collect-odds --provider misli-public --snapshot data\misli-public-snapshot.sample.json
```

These commands reject incomplete Misli rows, record live-run errors, and do not import matches without a full kickoff datetime.

`run-live-paper-cycle` should orchestrate a safe subset:

```text
collect matches
collect odds
generate features
generate predictions
write paper bets
record run summary
```

Task 41 implemented:

```powershell
python -m app.cli run-live-paper-cycle --provider misli-public --snapshot <snapshot.json> --model elo
```

The command prints counters for each stage and writes a cycle-level `live_runs` entry. Task 46 scoped the feature, prediction, and paper-bet stages to the match ids resolved from the requested snapshot so mixed databases do not process unrelated scheduled matches. Settlement remains explicit.

Settlement should remain explicit at first because result availability and timing are provider-dependent.

Task 42 implemented manual result collection:

```powershell
python -m app.cli collect-results --provider manual --path <results.json>
python -m app.cli settle-results
```

`collect-results` updates matches by `source + source_match_id` and records a `live_runs` entry. `settle-results` remains the existing explicit settlement command.

Task 50 implemented the one-shot scheduled paper worker:

```powershell
python -m app.cli run-scheduled-paper-worker --provider misli-public --snapshot <snapshot.json> --model baseline_heuristic
```

The worker records `live_runs.run_type='scheduled_paper_worker'`, refuses to run unless `LIVE_COLLECTION_ENABLED=true`, skips when another worker run is already `running`, and delegates the paper cycle to `run-live-paper-cycle` behavior. It intentionally does not perform settlement.

Task 67 added fresh snapshot URL support:

```powershell
python -m app.cli run-scheduled-paper-worker --provider misli-public --snapshot-url https://<host>/misli/latest.json --model baseline_heuristic
```

The worker downloads HTTPS JSON snapshots into `data/live-snapshots/`, runs the scoped live paper cycle, then refreshes paper recommendations, paper combinations, and deterministic AI recommendation review after a successful cycle. If `--snapshot-url` is absent, the worker still accepts `--snapshot` for deterministic fixtures or manually supplied files.

## Error Handling

Provider or normalization failures should:

- increment `errors_count`
- write structured error details
- skip the affected match/odds/result when safe
- keep the run alive for unrelated records
- return non-zero only for systemic failure

Examples of systemic failure:

```text
database unavailable
provider credentials invalid
provider response schema completely incompatible
configuration invalid
```

## Dashboard Requirements

The dashboard should gain a process monitor after live run registry exists.

Minimum read-only surfaces:

```text
latest live run status
last successful provider collection
errors_count and skipped records
latest paper bets written
open paper bets awaiting settlement
settlement status
provider/source health
```

No live execution controls in the first dashboard monitor unless explicitly approved later.

Task 44 implemented the first read-only monitor in the React dashboard. It consumes Task 43 endpoints and displays latest run status, provider/source label, counters, open/settled paper-bet counts, total errors, and last success/failure labels.

## Implementation Order

Build in this order:

1. Task 38 - Live Provider Contract
2. Task 39 - Live Run Registry
3. Task 40 - Manual Live Collection Commands
4. Task 41 - Live Paper Cycle Orchestrator
5. Task 42 - Live Result Collection And Settlement Flow
6. Task 43 - Live Process Status API
7. Task 44 - Dashboard Process Monitor
8. Task 45 - End-To-End Live Paper Dry Run
9. Task 46 - Live Cycle Run Scoping
10. Task 47 - Misli Kickoff Date Extraction
11. Task 48 - AI-Assisted Analyst Layer
12. Task 52 - Provider Health AI Analysis
13. Task 49 - Railway And Postgres Readiness
14. Task 50 - Scheduled Paper Worker

Do not skip Tasks 38 and 39. The provider contract and run registry are the foundation for reliable implementation and future agent handoffs.

## Acceptance For Phase Completion

Task 45 proved this local dry run is repeatable with deterministic fixtures:

```powershell
python -m app.cli collect-matches --provider <provider> --league <league> --lookahead-hours 72
python -m app.cli collect-odds --provider <provider> --league <league>
python -m app.cli run-live-paper-cycle --provider <provider> --league <league> --model elo
python -m app.cli collect-results --provider <provider> --league <league>
python -m app.cli settle-results
python -m app.cli evaluate
```

and:

```text
re-running commands does not duplicate core records
errors are visible in run registry
dashboard shows latest process status
full tests/lint/smoke pass
```

Real Misli public import is partially complete. Task 47 imports rows with full dates or high-confidence relative date labels and rejects bare time-only rows with live-run errors.

Task 46 resolved the P3 run-scoping debt: `run-live-paper-cycle` now processes only the intended snapshot match ids instead of all scheduled matches in the active database.

Task 50 added `run-scheduled-paper-worker` as the first scheduler-safe one-shot entrypoint. It is ready for external cadence configuration but still depends on Task 53 scraper hardening before real Misli public data should be trusted continuously.

Task 60 added deployed worker monitoring. `GET /api/live/worker-status` reports whether the latest `scheduled_paper_worker` run is fresh, stale, failed, running, or missing. `production-smoke` now checks API health, database health, worker freshness, recommendation endpoint response, report catalog, and optional dashboard HTML.

Task 61 added operational guardrails. `GET /api/operations/guardrails` and `operational-status` roll up worker freshness, repeated worker failures, provider data-quality warnings, AI eval failures, and empty recommendation cycles. The dashboard renders these as operator-visible `ok`, `warning`, or `critical` states before paper recommendations are trusted.

Task 53 hardened Misli public snapshot parsing and health reporting. Misli imports now fail closed for empty identity fields, incomplete odds, empty snapshots, and low extraction confidence. Provider-health AI analysis distinguishes parser drift, stale snapshots, and low extraction confidence from generic validation errors.

Task 54 added read-only odds movement summaries computed from existing `odds_snapshots`. The API can report opening odds, previous odds, current odds, movement direction, missing outcomes, and stale outcomes without inferring bet placement or bookmaker account state.

Task 55 added deterministic paper recommendations. `generate-recommendations` reads odds movement and model predictions, persists graded advisory records, rejects unsafe/weak candidates with explicit risk flags, and exposes them through `GET /api/live/recommendations`. It does not create `paper_bets`; actual paper bet logging remains a separate controlled stage.

Task 56 added ranked paper-only combinations. `generate-combinations` reads eligible active recommendations, rejects duplicate event exposure and unsafe legs, computes combined odds/probability/EV/confidence, persists `paper_combinations`, and exposes them through `GET /api/live/combinations`. Combination records remain advisory and do not create or execute bets.

Task 57 added AI-assisted recommendation review. `analyze-recommendations` reads persisted recommendations, combinations, provider health, and latest evaluation context, persists `recommendation_review` records in `ai_analysis_runs`, and exposes the latest review through `GET /api/ai/recommendation-review/latest`. The review can approve, caution, or reject paper recommendations, but remains advisory and cannot override deterministic gates.

Task 58 added dashboard inspection for the live recommendation loop. The React dashboard can now show recommendations, combinations, odds movement, risk flags, and the latest AI recommendation review in one read-only panel with filters.

Task 59 added historical recommendation backtesting for the live recommendation loop. `backtest-recommendations` evaluates settled persisted recommendations and combinations, exports singles-versus-combination performance with calibration and drawdown metrics, and writes a dashboard-compatible report companion. `analyze-recommendation-backtest` records an AI-assisted advisory summary for the backtest.

Task 67 added fresh snapshot consumption for scheduled workers. The worker can now consume an HTTPS JSON snapshot URL and refresh recommendations, combinations, and AI review after successful collection.

Task 68 added the next source step: a token-protected API latest-snapshot store plus a browser-enabled Misli producer that can POST public snapshot JSON into the API. The intended production flow is `Misli public page -> snapshot producer -> API latest snapshot endpoint -> worker WORKER_SNAPSHOT_URL -> recommendations/combinations/AI review -> dashboard`.

Task 69 resolves bare Misli `HH:MM` rows to the snapshot `scraped_at` local date. Rows still fail closed when the scrape timestamp is missing or invalid. This policy came from the first production fresh-snapshot proof, where the producer posted 21 events but the worker failed on one bare-time row.

## Non-Goals

- Real-money betting.
- Multi-user deployment.
- Cloud scheduling.
- Arbitrage execution.
- Protected scraping.
- Advanced ML changes.
- Provider marketplace abstraction beyond the first clean interface.
