# Task 78 - Production Journal Freshness

Status: completed

## Goal

Make the deployed daily dashboard show the paper journal and explicit combination quarantine state after each worker cycle.

## Requirements

- Generate a daily paper journal during successful scheduled worker runs.
- Include the generated journal id in scheduled worker CLI output.
- Normalize legacy multi-leg combination API and AI review payloads as experimental even if older database rows lack the `experimental_combination` flag.

## Implementation Notes

- `ScheduledPaperWorkerService` now calls `DailyPaperJournalService.generate()` after recommendation, combination, settlement, and AI review refreshes.
- `GET /api/live/combinations` now adds `experimental_combination` for legacy multi-leg rows at read time.
- AI recommendation review input applies the same legacy normalization.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_scheduled_paper_worker_service.py tests/unit/test_dashboard_api.py::test_live_combinations_endpoint_lists_ranked_paper_combinations tests/unit/test_ai_analysis_service.py::test_ai_analysis_service_records_recommendation_review_advisory tests/integration/test_cli.py::test_run_scheduled_paper_worker_command_records_worker_run -q
.\.venv\Scripts\python.exe -m ruff check app tests
```

## Next

Re-authenticate Railway CLI and verify a fresh production worker run creates `/api/live/daily-journal/latest`.
