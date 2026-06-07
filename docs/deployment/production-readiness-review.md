# Production Readiness Review

Date: 2026-05-22

Scope: paper-only AI-assisted betting intelligence system for local and Railway staging operation.

## Decision

Status: conditionally ready for continuous paper-only staging.

The project is deployed to Railway with a healthy API, Railway Postgres, public dashboard, a dedicated cron-managed worker service, and a scheduled public Misli snapshot producer. Railway cron-triggered paper worker cycles complete against Railway Postgres and deployed `production-smoke` passes against the public API plus dashboard URL. Task 82 refreshed this proof on 2026-06-07: worker run `2422` completed from a fresh public Misli snapshot with `errors_count=0`, operations behavior was `ok`, guardrails were `ok`, AI review and threshold review were fresh, the daily journal included threshold advice, and the public dashboard rendered the loop behavior panel. The 2026-05-28 post-audit live recommendation fix makes fresh Misli rows without local team history create cold-start predictions instead of `missing_prediction` recommendation records, rejects negative current-odds EV recommendations, and counts in-run recommendation records in guardrails.

## Safety Boundary

Pass:

- No real-money bet placement is implemented.
- No bookmaker account automation is implemented.
- No protected-path scraping is implemented.
- No CAPTCHA, Cloudflare, stealth, proxy, or bot-control bypass is implemented.
- Recommendation, combination, AI review, and backtest outputs remain advisory and paper-only.

## Local Verification Evidence

Required local verification for current readiness rechecks:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
cd dashboard
npm run test
npm run lint
npm run build
npm run smoke
```

Expected outcome:

```text
backend tests pass
Ruff passes
dashboard tests pass
dashboard lint passes
dashboard build passes
dashboard smoke passes
```

Any future readiness completion report must include fresh command results from the current turn.

## Deployed Railway Evidence

Status: current as of 2026-06-07.

Required after Railway service setup:

```powershell
python -m app.cli production-smoke --api-base-url https://<api-service>.up.railway.app --dashboard-url https://<dashboard-service>.up.railway.app
```

Required manual checks:

```powershell
curl https://<api-service>.up.railway.app/api/health
curl https://<api-service>.up.railway.app/api/live/status
curl https://<api-service>.up.railway.app/api/live/worker-status
curl https://<api-service>.up.railway.app/api/operations/guardrails
curl https://<api-service>.up.railway.app/api/live/recommendations?limit=5
curl https://<api-service>.up.railway.app/api/reports/comparisons
```

API, dashboard, scheduled-worker, and fresh public Misli snapshot-producer proof is complete for the current Railway services. Full daily-decision confidence still requires richer public/statistical football inputs beyond list-page odds.

Task 82 production proof on 2026-06-07:

```text
production-smoke.ok=true
latest_worker_run.id=2422
latest_worker_run.started_at=2026-06-07T18:01:32.738123+00:00
latest_worker_run.status=completed
latest_worker_run.errors_count=0
operations.guardrails.overall_status=ok
operations.behavior.overall_status=ok
recommendation_quality.overall_state=watchlist_only
recommendation_quality.actionable_count=0
recommendation_quality.watchlist_count=12
ai_review.id=617
threshold_review.id=618
daily_journal.id=3
daily_journal.threshold_overall_decision=fail_closed
dashboard.hasLoopBehavior=true
```

## Readiness Checklist

| Area | Status | Notes |
| --- | --- | --- |
| Offline sample pipeline | Pass | CLI import, feature, prediction, paper-bet, settlement, evaluation flow exists and is tested. |
| Historical replay and comparison | Pass | Football-Data import, replay, multi-bookmaker comparison, ranking, analysis, and dashboard reports are implemented. |
| Dashboard | Pass | React/Vite dashboard includes report catalog, charts, process monitor, AI analyst, recommendations, and guardrails. |
| Public Misli ingestion | Conditional | Public snapshot parser is validated and fail-closed, fresh snapshots are scheduled, but rendered DOM dependency and inferred bare time-only rows remain risks. |
| Live paper worker | Pass for staging setup | One-shot worker exists, refuses unsafe config, skips overlaps, and is monitored through worker status. |
| Recommendations | Conditional | Deterministic recommendations and combinations exist, but risk model remains simplified and requires larger paper backtests. |
| AI assistance | Pass for deterministic advisory mode | AI analysis records, prompt versions, eval gates, recommendation review, and backtest summaries exist. Optional LLM provider is not implemented. |
| Monitoring and guardrails | Pass | Worker freshness, repeated failures, provider quality, AI eval failure, and empty recommendation cycle guardrails are visible. |
| Railway deployment docs | Pass | Service topology, env vars, commands, smoke, rollback, and triage are documented. |
| Railway deployed API proof | Pass | API health, live status, worker freshness, recommendations, and comparison catalog passed deployed smoke against the Railway API URL. |
| Railway deployed dashboard proof | Pass | Dashboard HTML and rendered React mount verified at the Railway dashboard URL. |
| Railway scheduled worker proof | Pass | Dedicated Railway worker service ran successfully from cron and refreshed worker status. |

## Release Criteria

Before calling the system fully ready for continuous Railway staging:

1. API, dashboard, Postgres, and worker services are deployed on Railway.
2. API and worker services share the same Railway Postgres `DATABASE_URL`.
3. API and dashboard have `LIVE_COLLECTION_ENABLED=false`.
4. Worker has `LIVE_COLLECTION_ENABLED=true`.
5. Worker cadence is configured through Railway cron or equivalent scheduler.
6. `production-smoke` passes against deployed API and dashboard URLs.
7. `/api/operations/guardrails` returns `ok` or a known accepted warning.
8. At least one monitored worker cycle has completed without provider validation failure.
9. Any fresh Misli data source remains public/user-provided and paper-only.

## Residual Risks

- Misli public snapshot parsing depends on rendered DOM structure.
- Fresh public Misli snapshot generation is scheduled, but rendered DOM shape remains a provider risk.
- Bare time-only Misli kickoff rows resolve against trusted snapshot `scraped_at`, which remains less strong than explicit page date grouping.
- Recommendation expected value uses simplified unit-stake arithmetic.
- Threshold policy is auditable and active only after explicit approval/apply commands.
- Combination correlation and exposure controls remain heuristic.
- Odds movement is computed directly from snapshots instead of a dedicated summary table.
- External alert destination is not selected yet.
- Cold-start live predictions use neutral team-form inputs until richer club, player, schedule, and historical data sources are added.

## Final Position

The project is fit for monitored paper-only staging deployment, not autonomous betting and not real-money operation.

The next product phase is permitted football context enrichment so the probability model can improve before stronger active policy changes are approved.
