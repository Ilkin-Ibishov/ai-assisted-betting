# Task 79 - Product Timezone Journals

Status: completed

## Goal

Make daily paper journal dates follow the product timezone instead of the Railway container timezone.

## Requirements

- Add a product timezone setting with `Asia/Baku` as the default.
- Use the product timezone when generating a journal without an explicit `--journal-date`.
- Keep explicit journal dates unchanged.
- Cover UTC late-night rollover into the next Asia/Baku date.

## Implementation Notes

- Added `PRODUCT_TIMEZONE` / `Settings.product_timezone`.
- `DailyPaperJournalService` now computes default journal dates with `zoneinfo.ZoneInfo`.
- Scheduled worker and CLI journal generation pass the configured timezone.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_daily_paper_journal_service.py tests/unit/test_config.py tests/unit/test_scheduled_paper_worker_service.py tests/integration/test_cli.py::test_daily_paper_journal_command_persists_entry tests/integration/test_cli.py::test_run_scheduled_paper_worker_command_records_worker_run -q
.\.venv\Scripts\python.exe -m ruff check app tests
```

## Next

Deploy API and worker, then restart the worker once to verify `/api/live/daily-journal/latest` uses the Asia/Baku date.
