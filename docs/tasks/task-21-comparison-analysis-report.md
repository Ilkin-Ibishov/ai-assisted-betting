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
