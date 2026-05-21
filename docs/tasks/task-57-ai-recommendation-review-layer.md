# Task 57 - AI Recommendation Review Layer

## Goal

Make AI an advisory backbone for reviewing deterministic recommendations and combinations without replacing the statistical engine.

## Requirements

- Add an AI analysis mode for live recommendations and bet combinations.
- Use deterministic inputs only: model signals, odds movement, provider health, historical calibration, and recommendation metadata.
- Output structured review fields: summary, approval state, concerns, confidence explanation, rejected assumptions, and next checks.
- Use official OpenAI docs and secure credential handling if an LLM-backed provider is implemented.
- Keep deterministic fallback behavior available when no API key is configured.
- Add eval fixtures that fail closed on hype, real-money instructions, unsupported certainty, or missing risk caveats.

## Acceptance Criteria

- AI review can approve, caution, or reject paper recommendations.
- AI output is persisted and accessible through CLI/API/dashboard data.
- No AI response can instruct the system to place bets or automate bookmaker accounts.
- Tests cover deterministic fallback, unsafe output rejection, missing input rejection, and combination review.

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

Task 58 - Recommendation Dashboard.

## Blockers

Requires Task 55 and Task 56. LLM-backed provider requires secure OpenAI API configuration.

## Technical Debt

Track eval gaps for any AI mode that is introduced before broad historical validation.
