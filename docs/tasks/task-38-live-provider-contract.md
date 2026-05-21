# Task 38 - Live Provider Contract

## Goal

Define the provider interfaces, DTOs, and safety boundaries needed for live paper data collection.

## Requirements

- Add or formalize provider interfaces for matches, odds, and results.
- Define raw DTOs for live provider payloads before normalization.
- Add provider capability metadata.
- Keep providers read-only and database-agnostic.
- Document allowed provider behavior and blocked behavior.
- Add Misli public snapshot DTOs for the current Playwright JSON shape.
- Add validation that fails closed when required Misli fields are missing.

## Implementation Notes

Start from:

```text
docs/specs/live-paper-loop.md
docs/specs/data-providers.md
docs/specs/safety-and-compliance.md
```

First provider candidate:

```text
Misli.az public football snapshot
```

Discovery scope:

```text
public unauthenticated pages
public browser network requests
robots.txt allowed paths only
no login/account automation
no protected live-bet detail paths
no anti-bot bypass
```

Misli public discovery found usable football 1X2 odds in rendered unauthenticated DOM rows:

```text
docs/research/misli-public-discovery.md
tools/misli-public-snapshot.mjs
```

Treat this as a public snapshot source, not a direct database importer. Task 38 should model the snapshot with typed DTOs and capability metadata before Task 40 imports anything into SQLite.

Minimum Misli snapshot DTO fields:

```text
source
page_url
scraped_at
event_count
events[].source_match_id
events[].sport
events[].event_id
events[].home_team
events[].away_team
events[].kickoff_date
events[].kickoff_time
events[].league
events[].odds[].market
events[].odds[].selection
events[].odds[].odds_decimal
events[].raw_text
```

Validation rules:

```text
reject snapshot if source != misli_public
reject event import if source_match_id, home_team, away_team, or kickoff_time is missing
reject match import until a full kickoff datetime is available
reject odds import unless HOME, DRAW, and AWAY 1X2 odds are present
reject odds_decimal <= 1.0
preserve raw_text/raw_payload for audit
```

Expected code areas:

```text
app/providers/
app/services/
tests/unit/
```

## Acceptance Criteria

- Provider contract is typed and tested.
- Misli public snapshot DTOs and validation are typed and tested.
- Existing sample and Football-Data flows still pass.
- No provider writes directly to SQLite.
- No live source credentials or scraping bypass logic is introduced.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

## Implementation Status

Completed in code:

```text
app/providers/base.py
app/providers/misli_public.py
tests/unit/test_live_provider_contract.py
```

Implemented:

```text
ProviderCapability metadata model
MisliPublicSnapshot DTO
MisliPublicEvent DTO
MisliPublicOdd DTO
fail-closed source validation
fail-closed full kickoff datetime validation
fail-closed complete HOME/DRAW/AWAY 1X2 validation
odds_decimal > 1.0 validation
```

## Next

Task 39 - Live Run Registry.

## Blockers

Task 38 has no remaining contract blocker. The remaining Misli blocker belongs to Task 40: decide how to derive or reject full kickoff datetimes during import.

## Technical Debt

Track the current DOM-order 1X2 mapping and incomplete kickoff-date extraction in `docs/agent/05_TECHNICAL_DEBT.md`.
