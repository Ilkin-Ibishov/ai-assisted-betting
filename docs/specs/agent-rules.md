# 02 — Codex Agent Rules

## Role

You are the development agent implementing Paper Odds Lab.

Your job is to build a simple, correct, testable, production-style paper betting research system.

## Hard Rules

### 1. Do Not Implement Real-Money Betting

Do not place real bets.
Do not integrate deposit, withdrawal, payment, or bookmaker bet placement flows.

### 2. Do Not Implement Anti-Bot Bypass

Do not implement:

- Cloudflare bypass
- CAPTCHA bypass
- Browser fingerprint evasion
- Stealth browser automation
- Proxy rotation for evasion
- Login session abuse
- Rate-limit evasion

### 3. Keep MVP Small

Do not add:

- Telegram bot
- Advanced ML
- Multiple sports
- Multiple markets
- Live in-play betting
- Complex staking

unless explicitly requested later.

The user has now explicitly requested a local analytical dashboard. Dashboard work is allowed only within the accepted local-first, read-only dashboard plan in `docs/specs/dashboard.md` and `docs/decisions/ADR-0003-dashboard-stack.md`.

### 4. Prefer Deterministic Logic First

The first version must be explainable.

Use simple baseline models and rule-based decisions before advanced ML.

### 5. Logging Is Mandatory

Every major step must write logs.

No silent decisions.

### 6. Provider Abstraction Is Mandatory

Do not hardcode one data source into the core logic.

Use provider interfaces.

### 7. Backtesting Must Reuse Core Engine

Do not create a separate backtesting system with duplicated decision logic.

Historical/replay mode must use the same:

- FeatureBuilder
- PredictionEngine
- ValueDetector
- PaperBetLogger
- Evaluator

## Implementation Style

Use Python.

Recommended libraries:

```text
pydantic
sqlalchemy
pandas
typer
pytest
python-dotenv
```

Optional later:

```text
scikit-learn
apscheduler
streamlit
```

## Code Quality Requirements

- Type hints required.
- Small functions.
- Clear module boundaries.
- No hidden global state.
- No network calls in unit tests.
- Configuration through environment variables or config files.
- Store raw source payloads where useful.
- Validate all external data.

## Output Style

When implementing each phase, produce:

1. Code changes.
2. Short explanation.
3. Commands to run.
4. Tests added.
5. Known limitations.
