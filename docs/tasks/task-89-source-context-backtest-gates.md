# Task 89 - Source Context Backtest Gates

Status: planned

## Goal

Promote external-context evidence from visibility to a release gate before changing recommendation thresholds.

## Requirements

- Compare external-context and local-or-unknown recommendation buckets across hit rate, ROI, Brier score, log loss, drawdown, and sample size.
- Define minimum evidence gates before threshold policy approval.
- Treat small external-context samples as provisional.
- Include source-context gate status in AI review, daily journal, and behavior reports.
- Do not let external context automatically loosen thresholds without explicit governance approval.

## Acceptance Criteria

- Backtest output has a clear pass/provisional/fail status for source-context evidence.
- Threshold policy proposals cite whether source-context gates passed.
- Daily journal makes low-sample enriched evidence visible.
- Tests cover gate classification.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

## Next

After source-context gates mature, revisit whether the recommendation model needs richer licensed/statistical inputs beyond Football-Data CSV.

