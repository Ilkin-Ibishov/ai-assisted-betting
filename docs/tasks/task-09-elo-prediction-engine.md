# Task 09 - Elo Prediction Engine

## Goal

Add an explainable Elo-based prediction engine and make replay model selection explicit.

## Requirements

- Add `EloPredictionEngine`.
- Support model selection with:

```powershell
--model baseline_heuristic
--model elo
```

- Default remains `baseline_heuristic`.
- Elo ratings must use only matches completed before the candidate match kickoff.
- Keep the implementation deterministic and offline.
- Store predictions with:

```text
model_name=elo
model_version=v0
```

## MVP Elo Design

- Initial team rating: `1500`.
- K-factor: `20`.
- Home advantage: `65 Elo points`.
- Convert Elo difference to expected home win strength:

```text
home_strength = 1 / (1 + 10 ** (-elo_diff / 400))
```

- Use bookmaker normalized probability as the base probability.
- For `HOME`, adjust upward when Elo home strength is above `0.5`.
- For `AWAY`, adjust upward when Elo away strength is above `0.5`.
- For `DRAW`, keep adjustment small and conservative.
- Clamp model probabilities to `0.05..0.85`.

## Acceptance

Example:

```powershell
python -m app.cli replay-football-data --league E0 --season 2526 --bookmaker Avg --model elo --report-name e0_avg_elo
```

creates Elo predictions, paper bets, settlement, and evaluation reports.

## Technical Debt Note

Avoid scattering model-selection branches through services. Add a small model factory or equivalent helper.

