# Task 97 - Real Misli External Context Coverage

Status: in progress

## Goal

Prove which approved external football data source can cover real `misli:football:*` fixtures before importing any new context into model features.

## Business Requirement

The system should only resume paper-bet creation from recommendations with enough evidence to evaluate success probability. Current production recommendations remain cold-start because real Misli teams have no usable prior-history coverage.

## Source Decision

First probe target: API-Football / API-Sports.

Reason:

- Broad advertised competition coverage, including US and South American leagues that appear in Misli.
- Team search and fixture-history endpoints are available behind an API key.
- Free/low-cost plans make coverage validation cheap before deeper integration.

## Implementation Notes

- Added an API-Football provider client using `API_FOOTBALL_KEY`.
- Added `probe-external-context` CLI command.
- Added authenticated admin endpoint `POST /api/admin/external-context/probe`.
- The probe starts from the production-style Misli-only enrichment audit, searches provider team candidates, fetches recent fixture counts for candidates, and reports matched/ambiguous/unmatched teams.
- Added Misli transliteration query variants for common observed names such as `Kolo Kolo` -> `Colo Colo`, `Yunayted` -> `United`, and `Monarxs` -> `Monarchs`.
- Added live-observed variants for `Tayqers` -> `Tigers` and `Illinden` -> `Ilinden`.
- Added live-observed prefix/suffix search variants so names like `CF La Nucia`, `JK Tammeka Tartu U21`, and `Trival Valderas A.` can search as provider-friendly names.
- API-Football free plan exposes a 10 requests/minute and 100 requests/day limit, so the provider now paces requests by default.
- The probe now fetches fixture history only for plausible team-name matches instead of spending requests on weak candidates.
- Provider name matches without enough recent fixture history are reported as `insufficient_history`, not `matched`, because they are not usable enrichment coverage yet.
- The admin endpoint now accepts probe options in either query parameters or JSON body to avoid accidental default-size probes.
- Added a controlled API-Football context importer:
  - CLI: `python -m app.cli import-api-football-context`
  - Admin API: `POST /api/admin/external-context/import`
  - Defaults to `dry_run=true`.
  - Imports only teams classified as `matched`, meaning a strong provider team match with enough recent completed fixture history.
  - Writes completed history under source `api_football_context`, with provider IDs/raw payload preserved.
  - Does not create predictions, recommendations, paper bets, or threshold changes.
- Feature provenance now labels API-Football-sourced history as `external_context:api_football`.
- No predictions, recommendations, paper bets, or thresholds are changed by this task. The importer is explicit and dry-run by default.

## Live Probe Findings

Sampled from production public audit on 2026-06-14:

- Current audit had 19 scheduled Misli football fixtures and 38 unmatched team slots.
- API-Football account status returned active Free plan with 100 daily requests.
- Search-only sample used 8 provider calls and matched 4 of the first 5 unique teams:
  - `Qingdao Red Lions` -> exact match.
  - `Shanghai Port B` -> `Shanghai Port II`.
  - `Prospect United U20` -> `Prospect United`.
  - `Dulwich Hill U20` -> `Dulwich Hill`.
  - `Rockdale Illinden U20` needed the new `Illinden` -> `Ilinden` fallback.
- After Railway re-auth, `API_FOOTBALL_KEY` was set on the `ai-assisted-betting` production service and the service redeployed successfully.
- A correctly parameterized admin probe (`limit=1`) completed from production. A JSON-body probe before the endpoint fix accidentally used default `limit=20`, proving the endpoint needed safer body parsing.
- A production `limit=5` exact-search probe returned 5 unmatched teams, but direct provider searches showed 3 of those 5 could match by name with better query variants: `Tammeka Tartu`, `Trival Valderas`, and `La Nucia`.
- Follow-up production probe showed `Trival Valderas` matched by name but had 0 recent fixtures; the probe now keeps that separate from real matched coverage.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

Latest local result:

```text
321 passed
All checks passed!
```

No-key smoke:

```powershell
.\.venv\Scripts\python.exe -m app.cli probe-external-context --limit 2
```

Expected status without credentials:

```text
status=missing_credentials
required_env=API_FOOTBALL_KEY
```

## Next

- Add `API_FOOTBALL_KEY` in the target environment or local `.env`.
- Run `python -m app.cli probe-external-context --limit 20`, or call the admin endpoint with the configured bearer token.
- Use small probe limits on the free plan; a full team probe can consume the daily quota quickly.
- Start with dry-run imports and compare `/api/live/enrichment-audit` before/after any `dry_run=false` import.
- If dry-run imports improve coverage, run the importer with `dry_run=false` for a small limit and regenerate features in the next worker cycle.
- If coverage is weak or ambiguous, evaluate Sportmonks as the next provider.
