# Task 75 - Daily Paper Trading Journal

Status: planned

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

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_ai_analysis_service.py tests/unit/test_dashboard_api.py
.\.venv\Scripts\python.exe -m ruff check app tests
cd dashboard
npm run test
npm run lint
npm run build
```

## Next

Task 76 - Combination Risk Quarantine.

## Blockers

This task benefits from Task 71 because journal entries should cite the same quality cycle counts.

## Technical Debt

The system currently has operational facts and AI review facts, but not a first-class daily learning narrative. That makes progress harder to review over time.
