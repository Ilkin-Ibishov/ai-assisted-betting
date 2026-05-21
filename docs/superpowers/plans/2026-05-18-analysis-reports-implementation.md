# Analysis Reports Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a CLI analysis command that reads replay comparison JSON and prints concise interpretation guidance.

**Architecture:** Add a focused `ComparisonAnalysisService` that reads and validates comparison JSON, formats deterministic text sections, and returns the analysis string. Wire the service into `app/cli.py` through a new `analyze-comparison` command. Keep this first slice read-only: no new DB tables or output files.

**Tech Stack:** Python, Typer CLI, pytest, Ruff, existing JSON comparison report format.

---

## File Structure

- Create `app/services/analysis_service.py`
  - Owns comparison-report loading, validation, winner formatting, sample-size interpretation, disagreement notes, and next-experiment guidance.
- Modify `app/cli.py`
  - Adds `analyze-comparison --report <path>`.
  - Converts service validation failures into clear CLI errors.
- Create `tests/unit/test_analysis_service.py`
  - Unit coverage for formatting and validation.
- Modify `tests/integration/test_cli.py`
  - CLI coverage for successful analysis and missing report errors.
- Create `docs/tasks/task-21-comparison-analysis-report.md`
  - Records implementation summary, verification, next step, blockers, and technical debt.
- Modify `docs/specs/logging-and-evaluation.md`
  - Documents comparison analysis output and interpretation rules.
- Modify `docs/agent/02_IMPLEMENTATION_ORDER.md`
  - Marks Task 21 completed and identifies the next task after implementation.
- Modify `docs/agent/03_DOC_READING_MAP.md`
  - Keeps Task 21 references current.
- Modify `docs/agent/05_TECHNICAL_DEBT.md`
  - Update only if implementation introduces, changes, accepts, or resolves debt.

---

### Task 1: Add Analysis Service Validation

**Files:**
- Create: `app/services/analysis_service.py`
- Create: `tests/unit/test_analysis_service.py`

- [ ] **Step 1: Write failing tests for missing files and malformed report shape**

Add this to `tests/unit/test_analysis_service.py`:

```python
import json
from pathlib import Path

import pytest

from app.services.analysis_service import ComparisonAnalysisError, ComparisonAnalysisService


def test_analyze_comparison_report_rejects_missing_file(tmp_path: Path) -> None:
    report_path = tmp_path / "missing.json"

    with pytest.raises(ComparisonAnalysisError) as exc_info:
        ComparisonAnalysisService().analyze_comparison_report(report_path)

    assert str(report_path) in str(exc_info.value)
    assert "does not exist" in str(exc_info.value)


def test_analyze_comparison_report_requires_top_level_keys(tmp_path: Path) -> None:
    report_path = tmp_path / "comparison.json"
    report_path.write_text(json.dumps({"metadata": {}, "runs": []}), encoding="utf-8")

    with pytest.raises(ComparisonAnalysisError) as exc_info:
        ComparisonAnalysisService().analyze_comparison_report(report_path)

    assert str(report_path) in str(exc_info.value)
    assert "missing required field: rankings" in str(exc_info.value)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_analysis_service.py
```

Expected: fail with `ModuleNotFoundError: No module named 'app.services.analysis_service'`.

- [ ] **Step 3: Implement minimal validation service**

Create `app/services/analysis_service.py`:

```python
import json
from pathlib import Path
from typing import Any


class ComparisonAnalysisError(ValueError):
    pass


class ComparisonAnalysisService:
    def analyze_comparison_report(self, report_path: Path) -> str:
        report = self._load_report(report_path)
        self._validate_report(report_path, report)
        return "Comparison Analysis\n-------------------"

    def _load_report(self, report_path: Path) -> dict[str, Any]:
        if not report_path.exists():
            raise ComparisonAnalysisError(f"{report_path} does not exist")
        try:
            loaded = json.loads(report_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ComparisonAnalysisError(f"{report_path} is not valid JSON") from exc
        if not isinstance(loaded, dict):
            raise ComparisonAnalysisError(f"{report_path} must contain a JSON object")
        return loaded

    def _validate_report(self, report_path: Path, report: dict[str, Any]) -> None:
        for field in ["metadata", "rankings", "runs"]:
            if field not in report:
                raise ComparisonAnalysisError(
                    f"{report_path} missing required field: {field}"
                )
        if not isinstance(report["runs"], list) or not report["runs"]:
            raise ComparisonAnalysisError(f"{report_path} runs must be a non-empty list")
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_analysis_service.py
```

Expected: both tests pass.

---

### Task 2: Format Successful Analysis Output

**Files:**
- Modify: `app/services/analysis_service.py`
- Modify: `tests/unit/test_analysis_service.py`

- [ ] **Step 1: Write failing test for main analysis sections**

Add this helper and test to `tests/unit/test_analysis_service.py`:

```python
def _write_comparison_report(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "metadata": {
                    "league": "E0",
                    "season": "2526",
                    "models": ["baseline_heuristic", "elo"],
                    "bookmakers": ["B365", "Avg"],
                },
                "rankings": {
                    "best_roi": {
                        "model": "baseline_heuristic",
                        "bookmaker": "Avg",
                        "value": 0.121333,
                    },
                    "best_brier_score": {
                        "model": "elo",
                        "bookmaker": "Avg",
                        "value": 0.244022,
                    },
                    "best_log_loss": {
                        "model": "elo",
                        "bookmaker": "Avg",
                        "value": 0.681137,
                    },
                },
                "runs": [
                    {
                        "model": "baseline_heuristic",
                        "bookmaker": "B365",
                        "settled_bets": 59,
                        "total_bets": 59,
                        "roi": 0.114068,
                        "profit_loss_units": 6.73,
                        "brier_score": 0.25,
                        "log_loss": 0.70,
                        "roi_rank": 2,
                        "brier_score_rank": 3,
                        "log_loss_rank": 3,
                        "model_config": {"model_name": "baseline_heuristic"},
                    },
                    {
                        "model": "elo",
                        "bookmaker": "Avg",
                        "settled_bets": 62,
                        "total_bets": 62,
                        "roi": 0.022097,
                        "profit_loss_units": 1.37,
                        "brier_score": 0.244022,
                        "log_loss": 0.681137,
                        "roi_rank": 4,
                        "brier_score_rank": 1,
                        "log_loss_rank": 1,
                        "model_config": {"model_name": "elo"},
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def test_analyze_comparison_report_formats_winners_and_sample_warning(tmp_path: Path) -> None:
    report_path = tmp_path / "comparison.json"
    _write_comparison_report(report_path)

    output = ComparisonAnalysisService().analyze_comparison_report(report_path)

    assert "Comparison Analysis" in output
    assert f"Report: {report_path}" in output
    assert "League: E0" in output
    assert "Season: 2526" in output
    assert "Models: baseline_heuristic, elo" in output
    assert "Bookmakers: B365, Avg" in output
    assert "Runs: 2" in output
    assert "Best ROI: baseline_heuristic / Avg (0.121333)" in output
    assert "Best Brier score: elo / Avg (0.244022)" in output
    assert "Best log loss: elo / Avg (0.681137)" in output
    assert "Smallest settled sample: 59" in output
    assert "Largest settled sample: 62" in output
    assert "exploratory and should not be trusted as evidence of an edge" in output
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_analysis_service.py::test_analyze_comparison_report_formats_winners_and_sample_warning
```

Expected: fail because the service returns only a header.

- [ ] **Step 3: Implement formatting**

Replace `analyze_comparison_report` and add helpers in `app/services/analysis_service.py`:

```python
    def analyze_comparison_report(self, report_path: Path) -> str:
        report = self._load_report(report_path)
        self._validate_report(report_path, report)
        metadata = report["metadata"]
        rankings = report["rankings"]
        runs = report["runs"]
        settled_counts = [int(run.get("settled_bets") or 0) for run in runs]
        min_settled = min(settled_counts)
        max_settled = max(settled_counts)

        return "\n".join(
            [
                "Comparison Analysis",
                "-------------------",
                f"Report: {report_path}",
                f"League: {metadata.get('league')}",
                f"Season: {metadata.get('season')}",
                f"Models: {', '.join(metadata.get('models', []))}",
                f"Bookmakers: {', '.join(metadata.get('bookmakers', []))}",
                f"Runs: {len(runs)}",
                "",
                "Winners",
                "-------",
                f"Best ROI: {_format_winner(rankings.get('best_roi'))}",
                f"Best Brier score: {_format_winner(rankings.get('best_brier_score'))}",
                f"Best log loss: {_format_winner(rankings.get('best_log_loss'))}",
                "",
                "Sample Size",
                "-----------",
                f"Smallest settled sample: {min_settled}",
                f"Largest settled sample: {max_settled}",
                f"Warning: {_sample_size_warning(settled_counts)}",
                "",
                "Interpretation",
                "--------------",
                _interpret_winners(rankings),
                "",
                "Next Experiment",
                "---------------",
                _next_experiment(settled_counts),
            ]
        )
```

Add module-level helpers:

```python
def _format_winner(winner: Any) -> str:
    if not isinstance(winner, dict):
        return "n/a"
    return f"{winner.get('model')} / {winner.get('bookmaker')} ({winner.get('value')})"


def _sample_size_warning(settled_counts: list[int]) -> str:
    if all(count < 300 for count in settled_counts):
        return "Result is exploratory and should not be trusted as evidence of an edge."
    if any(300 <= count < 500 for count in settled_counts):
        return "Result is directionally useful but still not conclusive."
    return "Sample is large enough for stronger comparison, but not proof of future profit."


def _winner_pair(winner: Any) -> tuple[object, object] | None:
    if not isinstance(winner, dict):
        return None
    return winner.get("model"), winner.get("bookmaker")


def _interpret_winners(rankings: dict[str, Any]) -> str:
    roi = _winner_pair(rankings.get("best_roi"))
    brier = _winner_pair(rankings.get("best_brier_score"))
    log_loss = _winner_pair(rankings.get("best_log_loss"))
    if roi is not None and brier is not None and log_loss is not None and roi != brier and roi != log_loss:
        return "Best ROI disagrees with calibration winners; treat ROI as exploratory until sample size improves."
    if brier is not None and brier == log_loss:
        return "Brier score and log loss agree on the strongest calibration run."
    return "Winners are mixed; compare larger samples before drawing conclusions."


def _next_experiment(settled_counts: list[int]) -> str:
    if any(count < 300 for count in settled_counts):
        return "Increase the replay date range or add leagues before drawing stronger conclusions."
    return "Compare additional bookmakers or model settings to test whether the result persists."
```

- [ ] **Step 4: Run unit tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\unit\test_analysis_service.py
```

Expected: all analysis service unit tests pass.

---

### Task 3: Add CLI Command

**Files:**
- Modify: `app/cli.py`
- Modify: `tests/integration/test_cli.py`

- [ ] **Step 1: Write failing CLI success test**

Add imports if needed:

```python
import json
```

Add this test to `tests/integration/test_cli.py`:

```python
def test_analyze_comparison_command_prints_analysis(tmp_path) -> None:
    runner = CliRunner()
    report_path = tmp_path / "comparison.json"
    report_path.write_text(
        json.dumps(
            {
                "metadata": {
                    "league": "E0",
                    "season": "2526",
                    "models": ["baseline_heuristic", "elo"],
                    "bookmakers": ["B365", "Avg"],
                },
                "rankings": {
                    "best_roi": {"model": "baseline_heuristic", "bookmaker": "Avg", "value": 0.12},
                    "best_brier_score": {"model": "elo", "bookmaker": "Avg", "value": 0.24},
                    "best_log_loss": {"model": "elo", "bookmaker": "Avg", "value": 0.68},
                },
                "runs": [
                    {
                        "model": "baseline_heuristic",
                        "bookmaker": "Avg",
                        "settled_bets": 60,
                        "total_bets": 60,
                        "roi": 0.12,
                        "profit_loss_units": 7.2,
                        "brier_score": 0.25,
                        "log_loss": 0.7,
                        "roi_rank": 1,
                        "brier_score_rank": 2,
                        "log_loss_rank": 2,
                        "model_config": {"model_name": "baseline_heuristic"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["analyze-comparison", "--report", str(report_path)])

    assert result.exit_code == 0
    assert "Comparison Analysis" in result.output
    assert "Best ROI: baseline_heuristic / Avg (0.12)" in result.output
    assert "Next Experiment" in result.output
```

- [ ] **Step 2: Write failing CLI error test**

Add this test:

```python
def test_analyze_comparison_command_reports_missing_file(tmp_path) -> None:
    runner = CliRunner()
    report_path = tmp_path / "missing.json"

    result = runner.invoke(app, ["analyze-comparison", "--report", str(report_path)])

    assert result.exit_code != 0
    assert str(report_path) in result.output
    assert "does not exist" in result.output
```

- [ ] **Step 3: Run CLI tests to verify they fail**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\integration\test_cli.py::test_analyze_comparison_command_prints_analysis tests\integration\test_cli.py::test_analyze_comparison_command_reports_missing_file
```

Expected: fail because `analyze-comparison` command does not exist.

- [ ] **Step 4: Implement CLI command**

Modify `app/cli.py`:

```python
from app.services.analysis_service import ComparisonAnalysisError, ComparisonAnalysisService
```

Add near the comparison commands:

```python
@app.command("analyze-comparison")
def analyze_comparison(
    report: Path = typer.Option(..., help="Comparison JSON report path."),
) -> None:
    try:
        typer.echo(ComparisonAnalysisService().analyze_comparison_report(report))
    except ComparisonAnalysisError as exc:
        raise typer.BadParameter(str(exc)) from exc
```

- [ ] **Step 5: Run CLI tests to verify they pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\integration\test_cli.py::test_analyze_comparison_command_prints_analysis tests\integration\test_cli.py::test_analyze_comparison_command_reports_missing_file
```

Expected: both tests pass.

---

### Task 4: Documentation Updates

**Files:**
- Create: `docs/tasks/task-21-comparison-analysis-report.md`
- Modify: `docs/specs/logging-and-evaluation.md`
- Modify: `docs/agent/02_IMPLEMENTATION_ORDER.md`
- Modify: `docs/agent/03_DOC_READING_MAP.md`
- Modify: `docs/agent/05_TECHNICAL_DEBT.md` only if debt changes

- [ ] **Step 1: Add task doc**

Create `docs/tasks/task-21-comparison-analysis-report.md`:

```markdown
# Task 21 - Comparison Analysis Report

## Goal

Turn comparison JSON reports into a concise CLI interpretation report.

## Requirements

- Add `analyze-comparison --report <comparison.json>`.
- Print comparison metadata, winners, sample-size warnings, interpretation notes, and next experiment guidance.
- Fail clearly for missing files, invalid JSON, missing top-level keys, or empty `runs`.

## Acceptance

The command prints a readable analysis for a valid comparison report and returns a clear non-zero error for missing reports.

## Implementation Notes

Implemented in `app/services/analysis_service.py` and `app/cli.py`.

What was done:

- Added `ComparisonAnalysisService`.
- Added `analyze-comparison`.
- Added unit and integration tests.

What's next:

- Decide whether to add persisted analysis artifacts or keep analysis as stdout-only for the next slice.

Blockers:

- None.

Technical debt:

- No new technical debt introduced.
```

- [ ] **Step 2: Update logging/evaluation spec**

Add a section after “Comparison Ranking Reports”:

```markdown
## Comparison Analysis Reports

`analyze-comparison` should read comparison JSON and print:

```text
comparison metadata
winners
sample-size warning
interpretation notes
next experiment guidance
```

Small samples below 300 settled bets are exploratory and should not be trusted as evidence of an edge. Samples from 300 to 499 settled bets are directionally useful but not conclusive. Samples at or above 500 settled bets are more useful for comparison but still not proof of future profit.
```

- [ ] **Step 3: Update implementation order**

In `docs/agent/02_IMPLEMENTATION_ORDER.md`, add Task 21 to completed tasks and set the next task to:

```text
Plan analysis persistence or next product phase
```

- [ ] **Step 4: Confirm reading map**

Ensure `docs/agent/03_DOC_READING_MAP.md` includes Task 21 and points to:

```text
docs/superpowers/specs/2026-05-18-analysis-reports-design.md
docs/tasks/task-21-comparison-analysis-report.md
docs/specs/logging-and-evaluation.md
```

---

### Task 5: Full Verification And Smoke Test

**Files:**
- No code edits unless verification fails.

- [ ] **Step 1: Run full test suite**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Expected: all tests pass.

- [ ] **Step 2: Run full lint**

Run:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
```

Expected: `All checks passed!`

- [ ] **Step 3: Generate or reuse a comparison report**

Run:

```powershell
$env:MIN_EDGE='0.01'
.\.venv\Scripts\python.exe -m app.cli compare-replays --league E0 --season 2526 --models baseline_heuristic,elo --bookmakers B365,Avg --from-date 2025-08-01 --to-date 2025-12-31 --min-history 5 --workers 2 --report-name e0_compare_analysis
```

Expected: `reports/e0_compare_analysis_comparison.json` exists.

- [ ] **Step 4: Smoke test analysis command**

Run:

```powershell
.\.venv\Scripts\python.exe -m app.cli analyze-comparison --report reports/e0_compare_analysis_comparison.json
```

Expected output includes:

```text
Comparison Analysis
Winners
Sample Size
Interpretation
Next Experiment
```

- [ ] **Step 5: Final response**

Report:

```text
what was done
what is next
blockers
technical debt or known limitations
verification evidence
```

Mention that no Git commit was made if the folder is still not a Git repository.
