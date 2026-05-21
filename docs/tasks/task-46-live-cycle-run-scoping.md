# Task 46 - Live Cycle Run Scoping

## Goal

Scope `run-live-paper-cycle` so each live run processes only the intended provider, snapshot, and collected match set.

## Requirements

- Avoid processing all scheduled matches in the active database.
- Track the match ids collected or selected for a cycle.
- Generate features, predictions, and paper bets only for that scoped set.
- Preserve duplicate protection.
- Keep the command paper-only and provider-safe.

## Acceptance Criteria

- Implemented: a live cycle with one snapshot only touches that snapshot's imported matches.
- Implemented: re-running the same cycle creates no duplicate matches, odds, predictions, or paper bets.
- Implemented: existing offline/replay commands keep their current behavior through unscoped prediction service methods.
- Implemented: tests cover mixed databases with unrelated scheduled matches.

## Implementation Notes

Task 46 added scoped prediction helpers:

```text
PredictionService.generate_features_for_matches(match_ids)
PredictionService.generate_predictions_for_matches(match_ids)
PredictionService.write_paper_bets_for_matches(match_ids)
```

`run-live-paper-cycle` now reads the requested snapshot, validates Misli events, resolves the imported `source + source_match_id` rows to database match ids, and passes that scoped set through feature generation, prediction generation, and paper-bet writing.

The original unscoped `generate_features`, `generate_predictions`, and `write_paper_bets` methods remain available for offline and replay workflows.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
cd dashboard
npm run test
npm run lint
npm run build
npm run smoke
```

## Next

Task 47 - Misli Kickoff Date Extraction.

## Blockers

None. This should happen before scheduling.

## Technical Debt

Resolved the existing P3 live cycle run-scoping debt.
