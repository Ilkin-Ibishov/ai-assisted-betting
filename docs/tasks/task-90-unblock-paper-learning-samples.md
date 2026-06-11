# Task 90 - Unblock Paper Learning Samples

Status: completed

## Goal

Unblock the live paper loop so it can create and settle enough paper-only samples for recommendation backtests and threshold-policy learning.

## Context

The June 11/12 production audit showed that the system was operationally healthy but commercially idle:

- Worker, snapshot, AI review, threshold review, and journal stages were fresh.
- Latest journal state was `no_candidates`.
- Latest threshold policy was advisory `fail_closed` with sample size `0`.
- Result jobs stayed due/pending because Misli result collection ran in preview mode.
- Paper-bet creation was too strict for cold-start positive-EV research samples.

## Changes

- Default `MISLI_RESULT_PREVIEW_MODE` to `false` so enabled result collection writes completed Misli results instead of only previewing them.
- Default `SCHEDULED_SETTLEMENT_ENABLED` to `true` so scheduled worker runs settle paper bets after result collection.
- Lower the paper-bet confidence floor from `0.5` to `0.1`.

## Rationale

Paper bets are research records, not real-money staking instructions. The previous `0.5` paper-bet confidence gate prevented cold-start candidates with positive edge and positive expected value from entering the ledger, which meant there were too few records to settle and too little data for threshold-policy learning.

The new floor still rejects tiny confidence noise, but allows positive-EV paper candidates with raw confidence around the observed live cold-start level (`0.133333`) to become auditable paper samples.

## Acceptance Criteria

- Scheduled worker defaults now perform paper result writes and settlement unless explicitly overridden by environment variables.
- Tiny confidence predictions remain blocked from paper-bet creation.
- Positive-EV low-confidence research samples can enter the paper ledger.
- Full backend tests pass.

## Verification

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
```

Result:

```text
ruff: All checks passed.
pytest: 274 passed.
```

## Next

Deploy to `main`, wait for a Railway-executed worker cycle, then audit whether new paper bets and completed result jobs start appearing. If result jobs still remain pending, the next fix should target Misli result-source coverage, not threshold policy.

