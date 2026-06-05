# Task 80 - Scheduled Threshold Review

Status: completed

## Goal

Make successful scheduled worker runs refresh threshold-review advice before generating the daily paper journal.

## Requirements

- Generate a recommendation backtest report during completed scheduled worker cycles.
- Persist a `recommendation_backtest_summary` AI analysis from that report.
- Generate the daily paper journal after the threshold review so the journal includes fresh threshold advice.
- Keep failed, skipped, and disabled worker paths unchanged.

## Implementation Notes

- `ScheduledPaperWorkerService` now exports a scheduled-worker recommendation backtest report under `reports/scheduled-worker`.
- The worker analyzes that report through the existing `AIAnalysisService.analyze_recommendation_backtest_report` path.
- `ScheduledPaperWorkerSummary` now carries `threshold_review_id` for the generated review.
- Existing journal logic now automatically links the fresh threshold review through `source_ids`.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_scheduled_paper_worker_service.py::test_scheduled_worker_runs_one_paper_cycle_when_enabled -q
.\.venv\Scripts\python.exe -m pytest tests/unit/test_scheduled_paper_worker_service.py tests/unit/test_daily_paper_journal_service.py tests/unit/test_recommendation_backtest_service.py tests/unit/test_ai_analysis_service.py -q
.\.venv\Scripts\python.exe -m pytest tests/integration/test_cli.py::test_run_scheduled_paper_worker_command_records_worker_run -q
```

## Next

Deploy API and worker, then trigger one worker run and confirm `/api/live/daily-journal/latest` no longer reports `threshold_review.overall_decision = missing`.
