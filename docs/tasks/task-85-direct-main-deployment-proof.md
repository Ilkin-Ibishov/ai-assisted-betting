# Task 85 - Direct Main Deployment Proof

Status: planned

## Goal

Make the solo-coder release path explicit: changes land directly on `main`, Railway production deploys from `main`, and every release proves the deployed commit before production success is claimed.

## Context

The Task 83/84 work was pushed to a feature branch and verified locally, but Railway production continued to run the previous `main` commit. That is not a code failure, but it is a release-process failure: pushed branch code was not production code.

## Requirements

- Treat `origin/main` as the active production release branch.
- After pushing to `main`, verify Railway services report the same commit hash.
- Run production smoke only after the deployed commit matches the pushed commit.
- Record deployment evidence in the task handoff or production-readiness doc.
- Keep the process PR-free unless the user explicitly asks for PRs later.
- Do not force-deploy uncommitted local files or generated reports.
- Redeploy the dashboard service with `railway up . --path-as-root --service dashboard` from `dashboard/` until the service is GitHub-linked or given a stable root-directory config.
- Do not use local `railway run --service worker` as proof for worker execution when production `DATABASE_URL` points at `postgres.railway.internal`; that private hostname is only resolvable inside Railway.

## Acceptance Criteria

- `main` contains the latest implementation commit.
- Railway API, worker, snapshot producer, and dashboard deployment metadata are checked after the push.
- New routes added by the release are checked against production when applicable.
- Any mismatch between pushed commit and deployed commit is reported as a deployment blocker, not a passing release.
- Dashboard root `/` returns 200 after any manual dashboard upload.
- A Railway-executed worker cron or deployment-run proves new worker code paths; local private-network failures are not counted as production worker failures.

## Verification

```powershell
git rev-parse origin/main
railway status --json
cd dashboard
railway up . --path-as-root --service dashboard --detach -m "Deploy dashboard frontend from main"
cd ..
.\.venv\Scripts\python.exe -m app.cli production-smoke --api-base-url https://ai-assisted-betting-production.up.railway.app --dashboard-url https://dashboard-production-0a69.up.railway.app
```

## Next

After release proof is reliable, continue with team alias coverage and threshold policy governance.
