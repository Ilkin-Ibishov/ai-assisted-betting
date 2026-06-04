# Task 75 - Daily Paper Trading Journal

Status: completed

## Goal

Create a daily paper-only trading journal that turns live recommendations, AI review, and settled outcomes into a learning record.

## Requirements

- Produce one daily journal entry summarizing:
  - what the system would have picked
  - what was blocked
  - why AI approved, cautioned, or rejected the slate
  - what settled since the previous journal
  - open paper bet status
  - recommendation quality cycle summaries
  - threshold or calibration observations
- Expose journal entries through CLI and API.
- Show the latest journal entry in the dashboard without replacing operational guardrails.
- Keep language paper-only and advisory.

## Acceptance Criteria

- A user can understand yesterday's paper decisions without reading raw tables.
- Journal entries distinguish "candidate exists" from "AI trusts the slate."
- Settled outcomes are linked back to the recommendation or paper bet that created them.
- Tests cover no-candidate, candidate-ready, AI-rejected, and settled-result journal states.

## Implementation Notes

- Prefer deterministic journal generation first.
- If an LLM-backed analyst is added later, it should summarize the deterministic journal rather than invent facts.
- Store enough source ids for traceability.

## Implementation Summary

- Added first-class `paper_journal_entries` persistence with one unique journal per date.
- Added `DailyPaperJournalService` for deterministic paper-only journal generation.
- Journal entries include decision state, picked/blocked/watchlist counts, AI approval summary, settled outcomes since the previous journal, open paper bet status, recommendation quality snapshot, calibration observations, and traceable source ids.
- Added `daily-paper-journal` CLI command.
- Added `GET /api/live/daily-journal/latest`.
- Added dashboard API client support and a compact latest-journal card in the daily betting card.
- Covered no-candidate, candidate-ready, AI-rejected, and settled-result journal states in tests.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_ai_analysis_service.py tests/unit/test_dashboard_api.py
.\.venv\Scripts\python.exe -m ruff check app tests
cd dashboard
npm run test
npm run lint
npm run build
```

Verified on 2026-06-04:

- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_daily_paper_journal_service.py tests/unit/test_dashboard_api.py tests/integration/test_cli.py -q` - 86 passed.
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_database.py tests/unit/test_recommendation_quality_service.py tests/unit/test_ai_analysis_service.py -q` - 39 passed after updating migration expectations.
- `.\.venv\Scripts\python.exe -m ruff check app tests` - passed.
- `cd dashboard; npm run test -- --run` - 54 passed.
- `cd dashboard; npm run lint` - passed.
- `cd dashboard; npm run build` - passed.

## Next

Task 76 - Combination Risk Quarantine.

## Blockers

Resolved by Task 71. Journal entries now cite recommendation quality-style counts and state.

## Technical Debt

Future work can add an LLM summary over the deterministic journal, but the source-of-truth journal remains deterministic and paper-only.
