# Task 48 - AI-Assisted Analyst Layer

## Goal

Add an explicit AI-assisted backbone that explains model/process results, flags anomalies, and recommends next paper-only research actions.

## Requirements

- Keep AI assistance advisory only; no real-money betting execution.
- Use structured local metrics as input, not raw uncontrolled chat context.
- Treat probabilistic models and deterministic risk policy as the source of truth.
- Do not use an LLM as the primary match-outcome predictor.
- Produce explainable summaries for:
  - live run failures
  - model comparison results
  - open and settled paper-bet state
  - data-quality anomalies
  - next experiment suggestions
- Store AI-generated analysis with enough metadata for audit.
- Make the feature optional through configuration.
- Add evals for safety, grounding, and structured-output validity.

## Acceptance Criteria

- Implemented: dashboard can show AI-assisted advisory notes and deterministic empty-state guidance.
- Implemented: backend tests cover deterministic live-status advisory input/output behavior.
- Implemented: AI analysis records include model name, prompt version, source ids, input JSON, and output JSON.
- Implemented: no API keys are required for the core paper-betting loop.
- Implemented: AI output is clearly labeled as advisory analysis, not betting instruction.
- Implemented: live-status prompts are versioned in a registry.
- Implemented: AI provider output is checked by fail-closed safety and structure evals.
- Implemented: AI analysis defaults are configurable without requiring an LLM key.
- Implemented: comparison reports can be persisted as structured AI advisory records.

## Implementation Notes

Task 48 first slice added:

```text
ai_analysis_runs persistence
deterministic_ai_fallback live-status advisory service
analyze-live-status CLI command
GET /api/ai/analysis/latest
GET /api/ai/analysis/runs
GET /api/ai/analysis/runs/{id}
dashboard AI analyst panel
frontend AI advisory summary helper
```

Task 48 follow-up added:

```text
app/services/ai_prompt_registry.py
app/services/ai_analysis_evals.py
AIAnalysisProvider boundary
DeterministicAIAnalysisProvider fallback
AI_ANALYSIS_MODE default deterministic
AI_ANALYSIS_MODEL_NAME default deterministic_ai_fallback
fail-closed status failed records when provider output violates eval gates
```

Task 48 comparison analyst slice added:

```text
ai-comparison-report-v1 prompt contract
DeterministicAIAnalysisProvider.analyze_comparison_report
AIAnalysisService.analyze_comparison_report
analyze-comparison-ai CLI command
model_comparison_summary AI analysis records
sample-size and ROI/calibration disagreement risk flags
```

The implementation remains intentionally deterministic by default. It creates the AI backbone data shape, dashboard surface, prompt contract, provider contract, eval gate, and comparison-report analyst mode without requiring an API key.

Optional LLM integration remains a future enhancement behind configuration and eval gates.

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

Return to Task 46 live cycle run scoping before scheduling, or add a provider-health analyst mode for Misli validation failures.

## Blockers

No blocker for deterministic AI assistance. Optional LLM-backed analysis requires official-provider implementation and secure credential handling.

## Technical Debt

The AI backbone still uses deterministic fallback output only in normal operation. Add optional LLM provider integration, richer experiment planner, and provider-health analyst mode before calling the AI layer product-complete.

## Reference Spec

Read:

```text
docs/specs/ai-assisted-backbone.md
```
