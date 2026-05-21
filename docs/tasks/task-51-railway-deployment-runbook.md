# Task 51 - Railway Deployment Runbook And Production Smoke

## Goal

Document and verify the Railway deployment process end to end.

## Requirements

- Write Railway setup steps.
- Document services, environment variables, build commands, start commands, migrations, and smoke checks.
- Include rollback and recovery notes.
- Run production-like smoke tests against the deployed or staging URL.
- Keep paper-only safety boundaries visible.

## Acceptance Criteria

- A new operator can deploy the project from the runbook.
- API health, dashboard load, live status, and dry-run visibility are smoke-tested.
- Deployment does not require local-only files except documented fixtures.
- Known limitations are documented.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
cd dashboard
npm run test
npm run lint
npm run build
```

## Next

Post-deployment hardening:

```text
provider reliability
AI-assisted analysis refinement
model quality improvements
additional markets
operations alerts
```

## Blockers

Requires Railway project access and deployment credentials.

## Technical Debt

Record any manual deployment steps that remain after the first successful staging deploy.
