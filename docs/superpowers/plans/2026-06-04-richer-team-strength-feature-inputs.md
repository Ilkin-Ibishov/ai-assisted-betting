# Richer Team Strength Feature Inputs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add deterministic, auditable feature enrichment tiers from data the system already owns.

**Architecture:** Extend `FeatureBuilder` and `PredictionInput` with provenance fields computed from completed matches and existing odds snapshots. Persist provenance in existing text fields first so the slice avoids a schema migration, then expose it through prediction reasons and AI recommendation review.

**Tech Stack:** Python, SQLAlchemy ORM, pytest, Typer CLI, deterministic heuristic prediction engine.

---

### Task 1: Feature Enrichment Provenance

**Files:**
- Modify: `app/core/feature_builder.py`
- Test: `tests/unit/test_core_engine.py`

- [x] **Step 1: Write failing feature-builder tests**

Add tests that call `FeatureBuilder(allow_cold_start_features=True).build_for_match(...)` with missing, partial, and full historical context. Assert `feature.enrichment_tier`, `feature.feature_provenance`, `feature.home_rest_days`, `feature.away_rest_days`, `feature.home_goal_difference_trend_5`, `feature.away_goal_difference_trend_5`, and `feature.odds_movement_velocity` values.

- [x] **Step 2: Run tests to verify failure**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_core_engine.py -q`
Expected: FAIL because `BuiltFeature` has no enrichment/provenance fields.

- [x] **Step 3: Implement minimal enrichment fields**

Add fields to `BuiltFeature`, compute tier from history counts, compute rest days and goal-difference trends from existing completed matches, compute odds velocity from multiple snapshots for the same selection, and return deterministic provenance labels.

- [x] **Step 4: Run tests to verify pass**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_core_engine.py -q`
Expected: PASS.

### Task 2: Prediction Changes Only When Enriched

**Files:**
- Modify: `app/core/prediction_engine.py`
- Test: `tests/unit/test_core_engine.py`

- [x] **Step 1: Write failing prediction tests**

Add one test proving baseline predictions remain unchanged with `enrichment_tier="cold_start"` and another proving a full enriched home-strength signal changes probability upward.

- [x] **Step 2: Run tests to verify failure**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_core_engine.py -q`
Expected: FAIL because prediction inputs do not accept enriched fields.

- [x] **Step 3: Implement minimal prediction use**

Extend `PredictionInput` with enrichment fields. Add a small, clamped enriched adjustment only when `enrichment_tier` is `partial_enriched` or `full_enriched`.

- [x] **Step 4: Run tests to verify pass**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_core_engine.py -q`
Expected: PASS.

### Task 3: Carry Provenance Into Prediction And AI Review

**Files:**
- Modify: `app/services/prediction_service.py`
- Modify: `app/services/ai_analysis_service.py`
- Test: `tests/unit/test_ai_analysis_service.py`

- [x] **Step 1: Write failing AI review test**

Seed an active recommendation with prediction reason text containing `feature_tier=cold_start`; assert AI review risk flags include `odds_only_actionable_recommendations`. Seed another with `feature_tier=full_enriched`; assert model quality counts enriched recommendations.

- [x] **Step 2: Run test to verify failure**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_ai_analysis_service.py -q`
Expected: FAIL because feature provenance is not surfaced in review input/output.

- [x] **Step 3: Implement provenance pass-through**

Append `feature_tier=<tier>` and `feature_provenance=<labels>` to prediction reason when generating predictions. Parse that reason from recommendations in AI review input and add model-quality counts plus odds-only actionable risk flag.

- [x] **Step 4: Run tests to verify pass**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_ai_analysis_service.py -q`
Expected: PASS.

### Task 4: Docs And Verification

**Files:**
- Modify: `docs/tasks/task-74-richer-team-strength-feature-inputs.md`
- Modify: `docs/agent/02_IMPLEMENTATION_ORDER.md`
- Modify: `docs/agent/05_TECHNICAL_DEBT.md`

- [x] **Step 1: Update task docs**

Mark Task 74 completed and describe the deterministic local-data enrichment slice.

- [x] **Step 2: Run full verification**

Run:
`.\.venv\Scripts\python.exe -m pytest tests/unit/test_core_engine.py tests/unit/test_recommendation_service.py tests/unit/test_ai_analysis_service.py -q`
`.\.venv\Scripts\python.exe -m ruff check app tests`

- [x] **Step 3: Commit**

Run:
`git add app docs tests`
`git commit -m "Add richer team strength feature provenance"`
