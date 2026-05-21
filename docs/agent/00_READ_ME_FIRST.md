# Read Me First

Paper Odds Lab is an offline-first football paper betting research engine.

The goal is to build an auditable research pipeline:

```text
Sample data -> Normalization -> SQLite -> Features -> Predictions -> Value detection -> Paper bets -> Settlement -> Evaluation
```

The MVP must work locally without network access before any live or historical provider is added.

## Current State

The project has a working offline SQLite pipeline, Football-Data CSV import, historical replay, Elo and baseline prediction modes, replay comparison reports, model configuration metadata, comparison ranking annotations, deterministic comparison analysis output, and a local analytical dashboard.

The first "AI-assisted" product layer is now implemented as a deterministic backbone slice: `ai_analysis_runs`, `analyze-live-status`, `analyze-comparison-ai`, `analyze-provider-health`, read-only AI analysis API endpoints, and a dashboard AI analyst panel. Task 48 follow-up work added a prompt registry, provider boundary, AI analysis config defaults, fail-closed eval checks, and comparison-report analyst records. Task 52 added provider-health analyst records over `live_runs`. Current intelligence is still mostly statistical/model-based plus deterministic advisory analysis. Optional LLM-backed analysis, richer experiment planning, and deployment-readiness analysis remain future work.

The dashboard stack is:

```text
Frontend: React + TypeScript + Vite
UI: shadcn/ui + Tailwind CSS
Charts: Recharts
Tables: TanStack Table
Data fetching/state: TanStack Query
API layer: FastAPI
```

The next major product direction is a paper-only live loop. Start with:

```text
docs/specs/live-paper-loop.md
docs/tasks/task-45-end-to-end-live-paper-dry-run.md
docs/research/misli-public-discovery.md
```

Do not implement real-money betting or protected scraping. The live phase must remain paper-only and local-first.

Misli.az public football snapshot discovery now exists at `tools/misli-public-snapshot.mjs`, Task 38 formalized its DTO validation in `app/providers/misli_public.py`, Task 39 added the SQLite-backed live run registry, Task 40 added manual snapshot collection commands, Task 41 added `run-live-paper-cycle`, Task 42 added manual result collection with settlement reuse, Task 43 added read-only live process status API endpoints, Task 44 added the read-only dashboard process monitor, Task 45 proved an end-to-end deterministic live paper dry run, Task 46 scoped live cycle prediction stages to snapshot match ids, and Task 47 added high-confidence relative kickoff-date resolution for Misli rows. Current public Misli rows with `Bu Gün HH:MM` or `Sabah HH:MM` can import; bare `HH:MM` rows still fail closed. Next tasks are provider-health AI analysis and Tasks 49-51 Railway deployment readiness.

Task 52 is now complete: provider-health AI analysis can explain recent `live_runs` provider failures, including Misli datetime ambiguity, through `python -m app.cli analyze-provider-health --provider misli_public`.

Task 49 is now complete: Railway/Postgres readiness is documented in `docs/deployment/railway-readiness.md`, `/api/health` is available for API health checks, and the dashboard can target deployed APIs through `VITE_API_BASE_URL`.

## First Milestone

The first milestone is complete only when this sequence works:

```bash
python -m app.cli init-db
python -m app.cli import-sample-data
python -m app.cli generate-features
python -m app.cli generate-predictions
python -m app.cli write-paper-bets
python -m app.cli settle-results
python -m app.cli evaluate
pytest
```

## Next Milestone

The next milestone is complete only when this dry-run sequence works with a permitted provider or deterministic fake/manual provider:

```bash
python -m app.cli collect-matches
python -m app.cli collect-odds
python -m app.cli run-live-paper-cycle
python -m app.cli collect-results
python -m app.cli settle-results
python -m app.cli evaluate
pytest
```

## Agent Rule

Do not load every doc by default. Read `03_DOC_READING_MAP.md`, then load only the docs for the current task.

## Completion Rule

Every implementation task must finish with documentation and verification:

1. Update `docs/agent/02_IMPLEMENTATION_ORDER.md`.
2. Add or update the task doc in `docs/tasks/`.
3. Update `docs/agent/03_DOC_READING_MAP.md` when new docs or workflows are added.
4. Update `docs/agent/04_OPEN_QUESTIONS.md` when decisions are resolved or new ambiguity appears.
5. Update `docs/agent/05_TECHNICAL_DEBT.md` when technical debt is introduced, changed, accepted, or resolved.
6. Update relevant `docs/specs/` files when behavior changes.
7. Run the full test suite and full lint check after documentation and code changes.

Do not claim completion until both documentation and verification are done.

Focused tests are useful during development, but they are not sufficient for completion.

Required full verification:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

## Completion Report

After each implementation task, write a concise report covering:

```text
what was done
what is next
blockers
technical debt or known limitations
```

If there are no blockers, say so explicitly.
Any technical debt mentioned in the completion report must also be recorded or updated in `docs/agent/05_TECHNICAL_DEBT.md`.
