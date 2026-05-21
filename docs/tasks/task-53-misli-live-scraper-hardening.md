# Task 53 - Misli Live Scraper Hardening

## Goal

Make Misli.az public football collection reliable enough for repeated paper-only live cycles.

## Requirements

- Keep collection limited to public football pages and user-approved manual browser/session context.
- Do not automate login, deposits, bet placement, CAPTCHA bypass, stealth, proxy rotation, or bookmaker account actions.
- Extract normalized event identity, league, teams, kickoff, odds, market type, and source metadata.
- Persist raw snapshot metadata for debugging while storing normalized events through the existing live provider contract.
- Detect UI/schema drift and fail closed with clear provider-health messages.
- Add fixture-based tests so parser behavior is stable even when the live site is unavailable.

## Acceptance Criteria

- Completed: Misli collection can run repeatedly without producing duplicate active events for the same match/market.
- Completed: invalid or partial rows fail closed with explicit reasons, including empty identity fields, incomplete 1X2 odds, empty snapshots, and low extraction confidence.
- Completed: provider-health analysis reports parser drift, stale snapshots, and low extraction confidence as explicit risk flags.
- Completed: tests cover Azerbaijani relative time labels, absolute date/time labels, malformed rows, empty snapshots, low extraction confidence, and comma-decimal odds parsing.

## Implementation Notes

- Hardened `app/providers/misli_public.py` to normalize comma decimal odds and reject empty identity/team/league/raw-text fields.
- Hardened `app/services/live_collection_service.py` to mark empty snapshots as possible parser drift and row-count mismatch as low extraction confidence.
- Updated `tools/misli-public-snapshot.mjs` to normalize comma decimal odds and include `extraction_summary` with skipped-row metadata.
- Updated deterministic provider-health analysis to emit:

```text
provider_parser_drift
provider_stale_snapshot
provider_low_extraction_confidence
```

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
cd dashboard
npm run test
npm run lint
npm run build
npm run smoke
```

## Next

Task 54 - Live Odds Movement Tracking.

## Blockers

None for the completed parser/provider-health hardening.

## Technical Debt

Selector drift remains open technical debt because the snapshot script still depends on rendered Misli DOM classes. The fallback behavior is fail-closed with parser-drift and low-confidence live-run errors.
