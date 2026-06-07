# Task 87 - Threshold Policy Governance And Decision Log

Status: planned

## Goal

Turn the threshold policy mechanism into an operator-safe governance workflow with explicit approval criteria and durable decision records.

## Requirements

- Define minimum settled sample sizes before approval.
- Define rules for tighten, disable, keep, loosen, and rollback decisions.
- Persist a human-readable decision log for approve, apply, and rollback actions.
- Link policy decisions to the backtest run and source-context evidence that justified them.
- Keep loosening conservative and advisory unless evidence is strong.

## Acceptance Criteria

- Policy approval cannot be interpreted without sample-size and outcome evidence.
- Every applied policy has a durable reason, actor, timestamp, and evidence reference.
- Rollback decisions are just as traceable as apply decisions.
- Daily journal and behavior reports expose the active policy decision reason.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_threshold_policy_service.py
.\.venv\Scripts\python.exe -m pytest
```

## Next

Expose safe policy controls in the dashboard after governance rules exist.

