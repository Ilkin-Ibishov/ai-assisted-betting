# Agent Instructions

This project is Paper Odds Lab: an offline-first football paper betting research engine.

## Hard Rules

- Do not place real-money bets.
- Do not automate bookmaker account actions.
- Do not implement anti-bot bypass, CAPTCHA bypass, Cloudflare bypass, stealth browser automation, proxy evasion, or protected scraping.
- Keep the MVP to football, pre-match, paper bets only, SQLite, and CLI-first workflows.
- Complete `SampleProvider` before any live API, replay, or historical provider.
- Core logic must be reusable across live, replay, and historical modes.
- Every major decision step must write an auditable decision log.

## Required Reading Order

1. Read this file.
2. Read `docs/agent/00_READ_ME_FIRST.md`.
3. Read `docs/agent/03_DOC_READING_MAP.md`.
4. Read only the task-specific docs listed in the reading map.

## Implementation Order

1. Bootstrap project
2. Database layer
3. Sample provider
4. Feature builder
5. Prediction engine
6. Value detector
7. Paper bet logger
8. Result settler
9. Evaluator
10. Full integration test

## Verification

Before claiming a task is complete, run focused tests for the changed area while developing, then run the full verification suite. Focused tests alone are not enough for completion.

Required full verification:

```bash
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

## Documentation Maintenance Rule

After each implementation task, update the agent-context and project docs before claiming completion:

1. Update `docs/agent/02_IMPLEMENTATION_ORDER.md`.
2. Add or update the task doc under `docs/tasks/`.
3. Update `docs/agent/03_DOC_READING_MAP.md` if new docs or workflows were added.
4. Update `docs/agent/04_OPEN_QUESTIONS.md` if decisions were resolved or new ambiguity appeared.
5. Update `docs/agent/05_TECHNICAL_DEBT.md` if technical debt was introduced, changed, accepted, or resolved.
6. Update relevant specs under `docs/specs/` if behavior changed.
7. Run the full test suite and full lint check after doc and code changes.
8. Do not claim completion until docs and verification are both done.

## Completion Report Rule

After each implementation task, include a short completion report with:

1. What was done.
2. What is next.
3. Any blockers.
4. Any technical debt or known limitations.

Keep the report concise, but do not omit blockers or technical debt.
Technical debt mentioned in the report must also be reflected in `docs/agent/05_TECHNICAL_DEBT.md`.
