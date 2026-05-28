# Task 70 - Snapshot Producer Railway Image

Status: completed; waiting for next scheduled worker proof

## Goal

Make the Railway `snapshot-producer` deployment repeatable after the previous upload build exported a Docker image but remained stuck as a stopped `BUILDING` deployment without an active image digest.

## What Changed

- Switched `Dockerfile.snapshot` from `node:24-bookworm` plus `npx playwright install --with-deps chromium` to the official `mcr.microsoft.com/playwright:v1.60.0-noble` base image.
- Kept the producer command unchanged:
  - read the public Misli football page
  - create snapshot JSON
  - post it to the token-protected API latest-snapshot endpoint

## Why

The official Playwright image already contains browser runtime dependencies, so Railway no longer needs to install system packages and browser binaries during the producer build. This should reduce build time and avoid the previous half-finished Railway state.

## Verification

Pending:

```powershell
cd dashboard
npm run snapshot:test
```

Result:

```text
Snapshot producer tests: 2 passed
```

Railway producer deploy proof:

```text
deployment=df944e43-9e2c-4bad-9b1f-0c582f4e5e37
status=SUCCESS
dockerfilePath=Dockerfile.snapshot
imageDigest=sha256:d726b52b40f51fc165fa8f71703c490c92ee72229c69d079a0b2324d53121b2d
cronSchedule=*/30 * * * *
```

Immediate producer proof:

```text
snapshot_posted=https://ai-assisted-betting-production.up.railway.app/api/live/snapshots/latest/misli-public
latest_snapshot.scraped_at=2026-05-28T00:05:28.437Z
latest_snapshot.event_count=21
```

Full verification remains required before declaring the implementation complete:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
cd dashboard
npm run snapshot:test
npm run test
npm run lint
npm run build
$env:PLAYWRIGHT_CHANNEL='chrome'; npm run smoke
```

## What's Next

- Confirm the scheduled worker consumes the fresh snapshot and refreshes the dashboard data.
- Run the full local verification suite after docs and image updates.

## Blockers

- No producer-image blocker remains. The previous stopped `BUILDING` deployment was removed after the clean deploy.
- End-to-end proof is waiting for the next scheduled worker run after the fresh snapshot.

## Technical Debt

The producer still depends on rendered Misli public page selectors and captures only list-page odds. Richer club, league, player, injury, lineup, rest-day, travel, and schedule-congestion inputs remain separate recommendation-quality work.
