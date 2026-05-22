# Production Readiness Review

Date: 2026-05-22

Scope: paper-only AI-assisted betting intelligence system for local and Railway staging operation.

## Decision

Status: conditionally ready for continuous paper-only staging.

The project is ready to deploy to Railway staging and run monitored paper-only cycles after Railway services, environment variables, and snapshot/cadence setup are configured. It is not yet fully production-proven because deployed Railway smoke evidence is still pending.

## Safety Boundary

Pass:

- No real-money bet placement is implemented.
- No bookmaker account automation is implemented.
- No protected-path scraping is implemented.
- No CAPTCHA, Cloudflare, stealth, proxy, or bot-control bypass is implemented.
- Recommendation, combination, AI review, and backtest outputs remain advisory and paper-only.

## Local Verification Evidence

Required local verification for Task 62:

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

The final Task 62 completion report must include fresh command results from the current turn.

## Deployed Railway Evidence

Status: pending.

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

Deployment cannot be called fully proven until these checks pass against real Railway URLs.

## Readiness Checklist

| Area | Status | Notes |
| --- | --- | --- |
| Offline sample pipeline | Pass | CLI import, feature, prediction, paper-bet, settlement, evaluation flow exists and is tested. |
| Historical replay and comparison | Pass | Football-Data import, replay, multi-bookmaker comparison, ranking, analysis, and dashboard reports are implemented. |
| Dashboard | Pass | React/Vite dashboard includes report catalog, charts, process monitor, AI analyst, recommendations, and guardrails. |
| Public Misli ingestion | Conditional | Public snapshot parser is validated and fail-closed, but rendered DOM dependency and bare time-only rows remain risks. |
| Live paper worker | Pass for staging setup | One-shot worker exists, refuses unsafe config, skips overlaps, and is monitored through worker status. |
| Recommendations | Conditional | Deterministic recommendations and combinations exist, but risk model remains simplified and requires larger paper backtests. |
| AI assistance | Pass for deterministic advisory mode | AI analysis records, prompt versions, eval gates, recommendation review, and backtest summaries exist. Optional LLM provider is not implemented. |
| Monitoring and guardrails | Pass | Worker freshness, repeated failures, provider quality, AI eval failure, and empty recommendation cycle guardrails are visible. |
| Railway deployment docs | Pass | Service topology, env vars, commands, smoke, rollback, and triage are documented. |
| Railway deployed proof | Pending | Requires Railway credentials, deployed service URLs, and successful production smoke. |

## Release Criteria

Before calling the system fully ready for continuous Railway staging:

1. API, dashboard, Postgres, and worker services are deployed on Railway.
2. API and worker services share the same Railway Postgres `DATABASE_URL`.
3. API and dashboard have `LIVE_COLLECTION_ENABLED=false`.
4. Worker has `LIVE_COLLECTION_ENABLED=true`.
5. Worker cadence is configured through Railway cron or equivalent scheduler.
6. `production-smoke` passes against deployed URLs.
7. `/api/operations/guardrails` returns `ok` or a known accepted warning.
8. At least one monitored worker cycle has completed without provider validation failure.
9. Any fresh Misli data source remains public/user-provided and paper-only.

## Residual Risks

- Misli public snapshot parsing depends on rendered DOM structure.
- Bare time-only Misli kickoff rows remain fail-closed until a safe date source is proven.
- Recommendation expected value uses simplified unit-stake arithmetic.
- Combination correlation and exposure controls remain heuristic.
- Odds movement is computed directly from snapshots instead of a dedicated summary table.
- External alert destination is not selected yet.
- Deployed Railway smoke evidence is pending.

## Final Position

The project is fit for monitored paper-only staging deployment, not autonomous betting and not real-money operation.

Advanced phases should wait until Railway deployed smoke passes and guardrail status has been observed during real scheduled paper cycles.
