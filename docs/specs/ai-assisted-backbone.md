# AI-Assisted Backbone

## Purpose

Make AI assistance a core product layer instead of a decorative dashboard feature.

The AI layer should help the user understand, audit, and improve the paper-betting system. It should not become an unchecked betting executor.

## Research Summary

External research and best-practice review points to a hybrid design:

```text
probabilistic sports model + calibration + deterministic risk policy + auditable AI analyst
```

Key findings:

- Betting prediction quality should prioritize probability calibration, not only accuracy.
- LLMs are better suited for structured analysis, explanation, anomaly detection, and planning than direct odds prediction.
- Agentic systems in financial or financial-adjacent domains need audit logs, deterministic policy gates, and human approval for high-risk actions.
- LLM applications need evals, prompt/model versioning, traceability, and continuous regression checks.

## Current State

Already implemented intelligence:

```text
baseline heuristic prediction model
Elo prediction model
value detection
ROI/Brier/log-loss evaluation
comparison ranking
deterministic comparison analysis
dashboard interpretation panels
live process monitor
```

Not yet implemented:

```text
LLM-backed analyst
AI-assisted experiment planner
```

Implemented by Task 48 first slice:

```text
AI analysis persistence
deterministic live-status advisory generation
AI analysis read API
analyze-live-status CLI command
dashboard AI analyst panel
```

Implemented by Task 48 follow-up:

```text
live-status prompt/version registry
AIAnalysisProvider boundary
deterministic provider fallback
AI_ANALYSIS_MODE and AI_ANALYSIS_MODEL_NAME config defaults
fail-closed advisory output evals
```

Implemented by Task 48 comparison analyst slice:

```text
comparison-report prompt/version registry
model_comparison_summary AI analysis persistence
analyze-comparison-ai CLI command
sample-size risk flags
ROI versus calibration disagreement flags
paper-only next experiment recommendation
```

Implemented by Task 52 provider-health analyst slice:

```text
provider-health prompt/version registry
provider_health_summary AI analysis persistence
analyze-provider-health CLI command
Misli datetime validation risk flags
provider failure source run ids
```

Implemented by Task 57 recommendation review slice:

```text
recommendation-review prompt/version registry
recommendation_review AI analysis persistence
analyze-recommendations CLI command
latest recommendation review API endpoint
approval_state, concerns, rejected assumptions, and next checks
fail-closed evals for hype, unsafe betting instructions, and missing inputs
```

## Recommended Architecture

### 1. Deterministic Data And Policy Core

This remains the source of truth:

```text
provider snapshots
normalized matches and odds
features
predictions
paper bets
settlement
evaluation
live_runs
```

The LLM must not directly mutate these records.

### 2. Probabilistic Model Layer

This estimates probabilities:

```text
baseline heuristic
Elo
future calibrated models
future ensemble model
```

Model outputs should be evaluated by calibration metrics:

```text
Brier score
log loss
reliability bins
expected calibration error when added
walk-forward validation
```

### 3. Deterministic Risk And Paper-Bet Policy

This decides whether a paper bet is written:

```text
minimum edge
odds range
duplicate protection
paper-only status
provider safety gate
future bankroll simulation rules
```

LLM output can explain or challenge this policy, but should not override it.

### 4. AI Analyst Layer

This is the AI backbone:

```text
Run Analyst
Model Analyst
Provider Analyst
Experiment Planner
Deployment/Operations Analyst
```

It reads structured snapshots from the system and writes advisory analysis records.

Suggested inputs:

```text
live status API payload
recent live_runs
comparison JSON
evaluation reports
provider validation errors
technical debt register
project rules and safety docs
```

Suggested outputs:

```text
short_summary
root_cause
risk_flags
recommended_next_actions
confidence
source_record_ids
prompt_version
model_name
created_at
```

### 5. Dashboard Integration

The dashboard should show AI assistance as:

```text
AI process summary
provider failure explanation
model health explanation
next experiment recommendation
data quality warnings
deployment readiness checklist
```

Every AI note must be labeled:

```text
AI-assisted advisory analysis
```

## Data Model Direction

Add an `ai_analysis_runs` table:

```text
id
analysis_type
source_type
source_id
input_json
output_json
model_name
prompt_version
status
error_summary
created_at
```

Possible `analysis_type` values:

```text
live_run_root_cause
model_comparison_summary
provider_health_summary
recommendation_review
next_experiment_plan
deployment_readiness_review
```

## API Direction

Read endpoints:

```text
GET /api/ai/analysis/latest
GET /api/ai/recommendation-review/latest
GET /api/ai/analysis/runs
GET /api/ai/analysis/runs/{id}
```

Command or worker entrypoints:

```powershell
python -m app.cli analyze-live-status
python -m app.cli analyze-comparison --report <path>
python -m app.cli analyze-comparison-ai --report <path>
python -m app.cli analyze-provider-health --provider misli_public
python -m app.cli analyze-recommendations
python -m app.cli plan-next-experiment
```

## Safety Rules

- AI outputs are advisory only.
- AI cannot place bets.
- AI cannot automate bookmaker accounts.
- AI cannot bypass provider protections.
- AI cannot override deterministic risk gates.
- AI cannot silently change model or betting configuration.
- Any future real-money action remains out of scope.

## Evals

AI assistance needs its own evals before production:

```text
Implemented: does not recommend real-money execution
Implemented: returns valid structured advisory JSON fields
Implemented: uses source ids from input records, except valid no_live_runs empty states
Implemented: keeps next actions within paper-only safety boundaries
Implemented: flags ROI/calibration disagreement in comparison reports
Implemented: identifies missing kickoff dates as provider blocker in provider-health mode
Implemented: rejects recommendation-review hype, real-money/account instructions, unsupported certainty, bad review shape, and missing deterministic inputs
Next: add stricter no-invented-facts fixtures across comparison report variants
```

## Implementation Order

1. Implemented: add local deterministic AI-analysis fallback summaries.
2. Implemented: add `ai_analysis_runs` persistence.
3. Implemented: add dashboard AI analyst panel.
4. Implemented: add prompt/version registry.
5. Implemented: add stricter live-status eval fixtures and regression tests.
6. Implemented: add model-comparison analyst mode over replay comparison JSON.
7. Implemented: add provider-health analyst mode over live provider runs.
8. Implemented: add recommendation and combination review analyst mode.
9. Next: add optional LLM provider integration behind configuration.
10. Next: add richer AI-assisted next-experiment planner.
11. Next: add deployment-readiness analyst mode.

## Non-Goals

- LLM-only match prediction.
- Real-money betting.
- Autonomous bookmaker actions.
- Private/protected scraping decisions.
- Replacing statistical calibration with prose confidence.
