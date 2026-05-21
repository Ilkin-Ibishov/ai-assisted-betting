# 04 — Database Schema

## Database

Use SQLite for local MVP and Railway Postgres for staging.

Recommended file:

```text
data/paper_odds_lab.sqlite
```

Use SQLAlchemy ORM or SQLModel.

## Tables

---

## 0. schema_migrations

Stores applied local SQLite migrations.

```sql
CREATE TABLE schema_migrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    migration_name TEXT NOT NULL UNIQUE,
    applied_at TEXT NOT NULL
);
```

This table is managed by `app/db/migrations.py`.

On Postgres, fresh databases are created from SQLAlchemy models and existing legacy migration names are recorded as model-managed no-ops. The legacy upgrade functions are SQLite-only because they patch older local SQLite files.

---

## 1. matches

Stores football matches.

```sql
CREATE TABLE matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    source_match_id TEXT NOT NULL,
    league TEXT NOT NULL,
    season TEXT,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    kickoff_time TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'scheduled',
    home_score INTEGER,
    away_score INTEGER,
    result TEXT,
    raw_payload_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(source, source_match_id)
);
```

### status values

```text
scheduled
in_progress
completed
postponed
cancelled
unknown
```

### result values

For 1X2:

```text
HOME
DRAW
AWAY
UNKNOWN
```

---

## 2. odds_snapshots

Stores odds at specific timestamps.

```sql
CREATE TABLE odds_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL,
    source TEXT NOT NULL,
    bookmaker TEXT NOT NULL,
    market TEXT NOT NULL,
    selection TEXT NOT NULL,
    odds_decimal REAL NOT NULL,
    implied_probability REAL NOT NULL,
    snapshot_time TEXT NOT NULL,
    minutes_before_kickoff INTEGER,
    is_closing BOOLEAN NOT NULL DEFAULT 0,
    raw_payload_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(match_id) REFERENCES matches(id),
    UNIQUE(match_id, source, bookmaker, market, selection, snapshot_time)
);
```

Task 54 uses `odds_snapshots` as the odds movement audit trail. Movement summaries are computed by grouping snapshots by:

```text
match_id, bookmaker, market, selection
```

The first observed odds become opening odds, the previous observed odds become previous odds, and the latest observed odds become current odds unless the outcome is missing from the latest market snapshot. No dedicated movement table exists yet.

### market values

MVP:

```text
1X2
OVER_UNDER_2_5
```

### selection values for 1X2

```text
HOME
DRAW
AWAY
```

### selection values for Over/Under 2.5

```text
OVER_2_5
UNDER_2_5
```

---

## 3. features

Stores generated features for match + market + selection.

```sql
CREATE TABLE features (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL,
    market TEXT NOT NULL,
    selection TEXT NOT NULL,

    home_form_points_5 REAL,
    away_form_points_5 REAL,
    home_goals_for_avg_5 REAL,
    away_goals_for_avg_5 REAL,
    home_goals_against_avg_5 REAL,
    away_goals_against_avg_5 REAL,
    home_advantage_flag INTEGER,

    bookmaker_probability REAL,
    bookmaker_margin_estimate REAL,

    home_elo_rating REAL,
    away_elo_rating REAL,

    feature_version TEXT NOT NULL,
    created_at TEXT NOT NULL,

    FOREIGN KEY(match_id) REFERENCES matches(id),
    UNIQUE(match_id, market, selection, feature_version)
);
```

---

## 4. predictions

Stores model predictions.

```sql
CREATE TABLE predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL,
    market TEXT NOT NULL,
    selection TEXT NOT NULL,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    model_probability REAL NOT NULL,
    bookmaker_probability REAL NOT NULL,
    edge REAL NOT NULL,
    confidence_score REAL,
    decision TEXT NOT NULL,
    reason TEXT,
    created_at TEXT NOT NULL,

    FOREIGN KEY(match_id) REFERENCES matches(id)
);
```

### decision values

```text
BET
SKIP
ERROR
```

---

## 5. paper_bets

Stores fake bets only.

```sql
CREATE TABLE paper_bets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_id INTEGER NOT NULL,
    match_id INTEGER NOT NULL,
    market TEXT NOT NULL,
    selection TEXT NOT NULL,
    odds_taken REAL NOT NULL,
    stake_units REAL NOT NULL,
    expected_value REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    profit_loss_units REAL,
    closing_odds REAL,
    clv REAL,
    settled_at TEXT,
    created_at TEXT NOT NULL,

    FOREIGN KEY(prediction_id) REFERENCES predictions(id),
    FOREIGN KEY(match_id) REFERENCES matches(id),
    UNIQUE(prediction_id)
);
```

### status values

```text
open
won
lost
void
cancelled
error
```

---

## 6. decision_logs

Stores structured logs for audit.

```sql
CREATE TABLE decision_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER,
    stage TEXT NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    input_json TEXT,
    output_json TEXT,
    warnings_json TEXT,
    errors_json TEXT,
    created_at TEXT NOT NULL,

    FOREIGN KEY(match_id) REFERENCES matches(id)
);
```

### stage values

```text
COLLECT_MATCHES
COLLECT_ODDS
NORMALIZE_MATCH
NORMALIZE_ODDS
BUILD_FEATURES
PREDICT
VALUE_DETECTION
WRITE_PAPER_BET
SETTLE_RESULT
EVALUATE
```

---

## 7. evaluation_runs

Stores evaluation summaries.

```sql
CREATE TABLE evaluation_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_name TEXT,
    market TEXT,
    model_name TEXT,
    model_version TEXT,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    total_bets INTEGER NOT NULL,
    won INTEGER NOT NULL,
    lost INTEGER NOT NULL,
    voided INTEGER NOT NULL,
    profit_loss_units REAL NOT NULL,
    roi REAL NOT NULL,
    hit_rate REAL,
    average_odds REAL,
    average_edge REAL,
    brier_score REAL,
    log_loss REAL,
    report_json TEXT,
    created_at TEXT NOT NULL
);
```

---

## 8. live_runs

Stores status and counters for live collection and live paper cycle runs.

```sql
CREATE TABLE live_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    run_type TEXT NOT NULL,
    provider TEXT NOT NULL,
    league TEXT,
    season TEXT,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    items_read INTEGER NOT NULL DEFAULT 0,
    items_created INTEGER NOT NULL DEFAULT 0,
    items_updated INTEGER NOT NULL DEFAULT 0,
    items_skipped INTEGER NOT NULL DEFAULT 0,
    errors_count INTEGER NOT NULL DEFAULT 0,
    error_summary TEXT,
    model_name TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(run_id)
);
```

### run_type values

Initial values:

```text
collect_matches
collect_odds
run_live_paper_cycle
collect_results
```

### status values

```text
running
completed
failed
```

## Indexes

Add indexes:

```sql
CREATE INDEX idx_matches_kickoff_time ON matches(kickoff_time);
CREATE INDEX idx_matches_status ON matches(status);
CREATE INDEX idx_odds_match_market ON odds_snapshots(match_id, market);
CREATE INDEX idx_odds_snapshot_time ON odds_snapshots(snapshot_time);
CREATE INDEX idx_predictions_match ON predictions(match_id);
CREATE INDEX idx_paper_bets_status ON paper_bets(status);
CREATE INDEX idx_decision_logs_match_stage ON decision_logs(match_id, stage);
CREATE INDEX idx_live_runs_status ON live_runs(status);
CREATE INDEX idx_live_runs_started_at ON live_runs(started_at);
CREATE INDEX idx_live_runs_provider_type ON live_runs(provider, run_type);
```

Identity constraints:

```sql
CREATE UNIQUE INDEX uq_odds_snapshot_identity
ON odds_snapshots(match_id, source, bookmaker, market, selection, snapshot_time);

CREATE UNIQUE INDEX uq_paper_bets_prediction_id
ON paper_bets(prediction_id);

CREATE UNIQUE INDEX uq_live_runs_run_id
ON live_runs(run_id);
```

---

## 10. paper_recommendations

Stores deterministic paper-only recommendation records created from predictions and live odds movement summaries.

```sql
CREATE TABLE paper_recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL,
    prediction_id INTEGER,
    source_run_id TEXT,
    source_match_id TEXT NOT NULL,
    bookmaker TEXT NOT NULL,
    market TEXT NOT NULL,
    selection TEXT NOT NULL,
    latest_snapshot_time TEXT NOT NULL,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    grade TEXT NOT NULL,
    status TEXT NOT NULL,
    model_probability REAL,
    implied_probability REAL,
    edge REAL,
    confidence_score REAL,
    current_odds REAL,
    expected_value REAL,
    risk_flags_json TEXT NOT NULL,
    rationale TEXT NOT NULL,
    created_at TEXT NOT NULL
);
```

Recommendation grades:

```text
recommended
lean
watch
reject
```

Recommendations are advisory and paper-only. They do not create real bets or automate bookmaker interactions.
