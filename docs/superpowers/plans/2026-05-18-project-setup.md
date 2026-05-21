# Project Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the runnable project shell and agent-facing documentation map for Paper Odds Lab.

**Architecture:** Keep the current source docs intact, create a separate implementation repo root, and copy normalized docs into `docs/`. Add `AGENTS.md` plus small agent docs so future Codex sessions know exactly what to read for each phase.

**Tech Stack:** Python 3.11+, Typer, Pydantic-compatible configuration, SQLAlchemy later, pytest, ruff.

---

### Task 1: Bootstrap Project Shell

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `README.md`
- Create: `app/`
- Create: `tests/`
- Create: `data/`
- Create: `reports/`

- [x] Create the directory structure from Task 01.
- [x] Add package metadata and dependencies.
- [x] Add placeholder CLI commands.
- [x] Add smoke tests for config and CLI help.

### Task 2: Add Agent Context Layer

**Files:**
- Create: `AGENTS.md`
- Create: `docs/agent/00_READ_ME_FIRST.md`
- Create: `docs/agent/01_RULES_AND_BOUNDARIES.md`
- Create: `docs/agent/02_IMPLEMENTATION_ORDER.md`
- Create: `docs/agent/03_DOC_READING_MAP.md`
- Create: `docs/agent/04_OPEN_QUESTIONS.md`

- [x] Add root agent rules.
- [x] Add task-specific reading map.
- [x] Record known spec contradictions before core implementation starts.

### Task 3: Verify Baseline

**Files:**
- Use: `tests/unit/test_config.py`
- Use: `tests/integration/test_cli.py`

- [x] Run `python -m app.cli --help`.
- [x] Run `pytest`.
- [x] Report setup status and remaining implementation order.
