# Task 15 - Record Model Configuration In Reports

## Goal

Make replay, evaluation, and comparison reports reproducible by recording the model configuration used for each run.

## Problem

Reports currently record the model name but not all configuration values, such as:

```text
ELO_INITIAL_RATING
ELO_K_FACTOR
ELO_HOME_ADVANTAGE
```

This makes it hard to reproduce or compare experiments after environment variables change.

## Requirements

Add `model_config` to:

- `evaluation_runs.report_json`
- replay summary JSON exports
- comparison JSON run entries

Minimum `model_config`:

```json
{
  "model_name": "elo",
  "model_version": "v0",
  "elo_initial_rating": 1500,
  "elo_k_factor": 20,
  "elo_home_advantage": 65
}
```

For non-Elo models, still include the Elo values because they are part of the experiment environment.

## Acceptance

Reports generated after replay and comparison include `model_config` values matching the active settings.

