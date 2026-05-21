# Task 11 - Elo Parameter Configuration

## Goal

Move Elo magic constants into configuration so replay experiments are reproducible and tunable.

## Config

Add:

```env
ELO_INITIAL_RATING=1500
ELO_K_FACTOR=20
ELO_HOME_ADVANTAGE=65
```

## Requirements

- Parse Elo values through `app.config.Settings`.
- Use `elo_initial_rating` when a team has no prior rating.
- Use `elo_k_factor` when updating historical ratings.
- Use `elo_home_advantage` both when building feature-time ratings and when predicting.
- Keep defaults matching the previous hardcoded behavior.
- Allow replay experiments to override values via environment variables.

## Acceptance

This should work:

```powershell
$env:ELO_HOME_ADVANTAGE='80'
python -m app.cli replay-football-data --league E0 --season 2526 --model elo
```

and produce Elo predictions using the configured value.

