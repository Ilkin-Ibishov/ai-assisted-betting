# Analysis Reports Design

## Goal

Add an offline analysis layer that turns replay comparison JSON into a concise, auditable interpretation report.

## Context

Paper Odds Lab already supports Football-Data CSV import, historical replay, baseline and Elo models, replay comparisons, ranking annotations, model configuration metadata, and diagnostic buckets. The next product phase should make those outputs easier to interpret before adding live collection or a dashboard.

## Scope

The first slice adds a CLI command:

```bash
python -m app.cli analyze-comparison --report reports/e0_compare_comparison.json
```

The command reads an existing comparison JSON file and prints a text analysis to stdout.

## Non-Goals

- No live collection.
- No bookmaker account automation.
- No browser dashboard.
- No model training or advanced ML.
- No rewriting of replay or comparison generation.

## Report Inputs

Input is a comparison JSON file produced by `compare-replays`.

Required fields:

```text
metadata
rankings
runs
```

Each run should include:

```text
model
bookmaker
total_bets
settled_bets
roi
profit_loss_units
brier_score
log_loss
roi_rank
brier_score_rank
log_loss_rank
model_config
```

## Report Output

The command should print sections in this order:

```text
Comparison Analysis
-------------------
Report:
League:
Season:
Models:
Bookmakers:
Runs:

Winners
-------
Best ROI:
Best Brier score:
Best log loss:

Sample Size
-----------
Smallest settled sample:
Largest settled sample:
Warning:

Interpretation
--------------
Best ROI disagrees with calibration winners; treat ROI as exploratory until sample size improves.

Next Experiment
---------------
Increase the replay date range or add leagues before drawing stronger conclusions.
```

## Interpretation Rules

Sample size:

- If every run has fewer than 300 settled bets, print that the result is exploratory and should not be trusted as evidence of an edge.
- If any run has at least 300 but fewer than 500 settled bets, print that the result is directionally useful but still not conclusive.
- If all runs have at least 500 settled bets, print that the sample is large enough for stronger comparison, while still not proof of future profit.

ROI and calibration:

- Best ROI and best calibration can point to different runs.
- If best ROI differs from both best Brier score and best log loss, call out the disagreement.
- If best Brier score and best log loss agree, call out the calibration winner.

Next experiment:

- Suggest increasing the date range or number of leagues when samples are below 300 settled bets.
- Suggest comparing additional bookmakers or model settings when samples are adequate.

## Error Handling

The command should fail clearly when:

- The report file does not exist.
- The file is not valid JSON.
- Required top-level keys are missing.
- `runs` is empty.

Error messages should identify the failing report path and the missing or invalid field.

## Architecture

Add a small service dedicated to report interpretation:

```text
app/services/analysis_service.py
```

Primary API:

```python
class ComparisonAnalysisService:
    def analyze_comparison_report(self, report_path: Path) -> str:
        return analysis_text
```

The CLI should call this service and print its returned string.

Keep the service pure except for reading the report file. It should not write new artifacts in the first slice.

## Testing

Add focused unit tests for:

- Winner formatting.
- Small sample warnings.
- Disagreement between ROI and calibration winners.
- Missing report file.
- Missing required keys.

Add CLI integration coverage for:

- `analyze-comparison --report <path>` prints the main sections.
- Missing report path returns a non-zero exit with a clear message.

## Documentation Updates

Update:

- `docs/agent/02_IMPLEMENTATION_ORDER.md`
- `docs/agent/03_DOC_READING_MAP.md`
- `docs/specs/logging-and-evaluation.md`
- a new task doc under `docs/tasks/`

## Approval Gate

Implementation should start only after this design is reviewed and approved.
