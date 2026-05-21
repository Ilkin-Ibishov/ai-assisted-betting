# Task 47 - Misli Kickoff Date Extraction

## Goal

Make real Misli public football snapshots importable by resolving full kickoff dates from safe public page context.

## Requirements

- Use only public unauthenticated Misli pages or user-provided snapshots.
- Do not automate login, CAPTCHA bypass, stealth, proxies, protected paths, or betting actions.
- Extract or validate full kickoff datetimes for public football rows.
- Keep fail-closed behavior when datetime confidence is insufficient.
- Update provider research notes with evidence.

## Acceptance Criteria

- Implemented: real Misli public snapshot rows either include validated full kickoff dates, derive them from high-confidence relative labels, or are rejected with a clear reason.
- Implemented: `collect-matches` can import real Misli rows only when full datetimes are present or safely resolved.
- Implemented: tests cover valid, missing, relative, and ambiguous date cases.
- Preserved: dashboard continues to show provider failure reasons through `live_runs`.

## Implementation Notes

Task 47 added a guarded date resolver in `app/providers/misli_public.py`:

```text
Bu Gün HH:MM -> scraped_at date in Asia/Baku
Sabah HH:MM -> scraped_at date + 1 day in Asia/Baku
bare HH:MM -> rejected unless a full kickoff_date is present
```

The resolver runs before Pydantic event validation and is also used by `LiveCollectionService` for per-event validation. The public snapshot tool still records raw page output; the provider layer owns the confidence decision.

Task 47 evidence from `data/misli-public-snapshot.task47.json`:

```text
events read: 21
collect-matches created: 20
collect-matches skipped: 1
collect-matches errors: 1
collect-odds created: 60
```

The skipped row had a bare time label without date context and correctly failed closed.

## Verification

```powershell
node tools\misli-public-snapshot.mjs --out data\misli-public-snapshot.task47.json
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

## Next

Provider-health AI analysis or Task 49 - Railway And Postgres Readiness.

## Blockers

No blocker for high-confidence relative-date Misli rows. Bare time-only rows remain blocked by design.

## Technical Debt

Narrowed the existing P2 Misli kickoff-date extraction debt. Relative date labels are resolved; bare time-only rows still fail closed.
