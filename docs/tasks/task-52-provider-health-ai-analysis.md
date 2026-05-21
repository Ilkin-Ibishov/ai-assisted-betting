# Task 52 - Provider Health AI Analysis

## Goal

Add an AI-assisted provider-health analyst that explains Misli/live provider validation failures and recommends paper-only engineering next actions.

## Requirements

- Read structured `live_runs` records, not raw chat context.
- Keep output advisory only and paper-only.
- Summarize completed versus failed provider runs.
- Identify provider validation failures, especially Misli datetime ambiguity.
- Store analysis in `ai_analysis_runs` for audit.
- Preserve fail-closed behavior for unsafe or malformed AI output.

## Acceptance Criteria

- Implemented: `analyze-provider-health --provider misli_public` creates a `provider_health_summary` record.
- Implemented: provider-health prompt is versioned as `ai-provider-health-v1`.
- Implemented: deterministic output flags `provider_datetime_missing` and `provider_failures_present` when recent Misli failures mention kickoff-date issues.
- Implemented: output cites source `live_runs` run ids.
- Implemented: output remains advisory and does not recommend real-money betting, account automation, proxy use, or CAPTCHA bypass.

## Implementation Notes

Task 52 added:

```text
PROVIDER_HEALTH_PROMPT_VERSION
ProviderHealthPrompt
build_provider_health_prompt
DeterministicAIAnalysisProvider.analyze_provider_health
AIAnalysisService.analyze_provider_health
analyze-provider-health CLI command
```

The deterministic provider-health analyst reads recent `live_runs` for a provider and stores:

```text
analysis_type: provider_health_summary
source_type: live_provider
source_id: provider key, for example misli_public
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

Task 49 - Railway And Postgres Readiness, then Task 50 scheduled paper worker.

## Blockers

No blocker for deterministic provider-health AI analysis.

## Technical Debt

No new technical debt. Remaining AI debt is optional LLM provider integration, richer experiment planning, and deployment-readiness analyst mode.
