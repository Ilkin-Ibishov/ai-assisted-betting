# Task 19 - Staged Model Selection

## Goal

Make manual staged CLI workflows able to select prediction models without changing environment variables.

## Problem

Replay workflows supported `--model`, but command-by-command staged workflows depended on `MODEL_NAME` from the environment. This made quick model switching awkward when running:

```bash
python -m app.cli generate-features
python -m app.cli generate-predictions
python -m app.cli write-paper-bets
```

## Requirements

- `generate-predictions` should accept:

```text
--model baseline_heuristic|elo
```

- `write-paper-bets` should accept the same `--model` option so it reads predictions for the selected model.
- Existing environment-based behavior should remain the default when `--model` is omitted.
- Tests should cover staged Elo prediction generation and staged Elo paper-bet selection.

## Acceptance

Staged commands can generate Elo predictions and run paper-bet selection for those Elo predictions without setting `MODEL_NAME`.

## Implementation Notes

Implemented in `app/cli.py`.

What was done:

- Added a shared CLI settings override helper for model selection.
- Added `--model` to `generate-predictions`.
- Added `--model` to `write-paper-bets`.
- Added integration tests for staged Elo prediction generation and paper-bet selection.

What's next:

- Decide whether to make comparison worker count configurable or move to the next product phase.

Blockers:

- None.

Technical debt:

- The replay-oriented model-selection debt is resolved.
- Comparison worker count remains fixed at 4 and is tracked in `docs/agent/05_TECHNICAL_DEBT.md`.
