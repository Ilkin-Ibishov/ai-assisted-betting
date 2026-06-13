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
- The probe starts from the production-style Misli-only enrichment audit, searches provider team candidates, fetches recent fixture counts for candidates, and reports matched/ambiguous/unmatched teams.
- Added Misli transliteration query variants for common observed names such as `Kolo Kolo` -> `Colo Colo`, `Yunayted` -> `United`, and `Monarxs` -> `Monarchs`.
- No imported matches, model features, predictions, recommendations, paper bets, or thresholds are changed by this task.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

Latest local result:

```text
307 passed
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
- Run `python -m app.cli probe-external-context --limit 20`.
- If coverage is good, add a controlled import path for confirmed team IDs and historical fixtures.
- If coverage is weak or ambiguous, evaluate Sportmonks as the next provider.
