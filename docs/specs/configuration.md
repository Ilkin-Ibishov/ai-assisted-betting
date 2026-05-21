# 11 — Configuration

## Config File

Use `.env` for local configuration.

Do not commit `.env`.

Create `.env.example`.

## Required Config

```env
DATABASE_URL=sqlite:///data/paper_odds_lab.sqlite

DEFAULT_SPORT=football
DEFAULT_MARKET=1X2
DEFAULT_STAKE_UNITS=1.0

MIN_EDGE=0.07
MIN_ODDS=1.70
MAX_ODDS=3.50

FEATURE_VERSION=v0_baseline
MODEL_NAME=baseline_heuristic
MODEL_VERSION=v0

ELO_INITIAL_RATING=1500
ELO_K_FACTOR=20
ELO_HOME_ADVANTAGE=65

LOG_LEVEL=INFO

AI_ANALYSIS_MODE=deterministic
AI_ANALYSIS_MODEL_NAME=deterministic_ai_fallback

LIVE_COLLECTION_ENABLED=false
VITE_API_BASE_URL=
```

## Optional Future Config

```env
DASHBOARD_API_HOST=127.0.0.1
DASHBOARD_API_PORT=8000
ODDS_API_KEY=
FOOTBALL_API_KEY=
```

## Config Rules

- Parse config once at startup.
- Validate numeric values.
- Fail clearly if invalid.
- Do not hardcode secrets.
- Do not print API keys.
- CLI `--model` options may override `MODEL_NAME` for a single command run.
- Keep `AI_ANALYSIS_MODE=deterministic` unless an LLM provider is explicitly implemented and verified.
- Do not require AI provider credentials for the core paper-betting loop.

## Environments

### local

SQLite, sample provider.

### paper-live

SQLite/PostgreSQL, live API provider.

### railway-staging

PostgreSQL plus FastAPI API service and static Vite dashboard.

API:

```env
DATABASE_URL=${{Postgres.DATABASE_URL}}
LIVE_COLLECTION_ENABLED=false
AI_ANALYSIS_MODE=deterministic
```

Dashboard:

```env
VITE_API_BASE_URL=https://<api-service>.up.railway.app
```

### replay

Historical CSV/replay provider.

### dashboard-local

FastAPI serves read-only report endpoints. React/Vite dashboard reads from the local API.

## Recommended Defaults

```text
min_edge = 0.07
min_odds = 1.70
max_odds = 3.50
stake_units = 1.0
market = 1X2
```
