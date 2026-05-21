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

- Misli collection can run repeatedly without producing duplicate active events for the same match/market.
- Invalid or partial rows are skipped with explicit reasons.
- Provider-health analysis reports parser drift, stale snapshots, and low extraction confidence.
- Tests cover Azerbaijani relative time labels, absolute date/time labels, malformed rows, and odds parsing.

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

Requires Task 50 scheduled worker or a manual repeated-run substitute.

## Technical Debt

If selectors remain brittle, document selector drift risks and the exact fallback behavior in `docs/agent/05_TECHNICAL_DEBT.md`.
