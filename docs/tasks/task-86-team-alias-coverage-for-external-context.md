# Task 86 - Team Alias Coverage For External Context

Status: planned

## Goal

Improve Misli-to-Football-Data matching so external football context is not limited to exact team-name matches.

## Requirements

- Add a deterministic team alias mapping layer with source, league, and confidence metadata.
- Keep aliases auditable and editable through local data files or database rows.
- Fail closed when an alias is ambiguous.
- Report unmatched Misli teams and alias coverage in CLI/API output.
- Backtest external-context recommendations before and after alias expansion.

## Acceptance Criteria

- Misli public team names can match Football-Data teams through explicit aliases.
- Ambiguous aliases do not silently enrich features.
- Backtest output shows external-context sample counts before and after alias use.
- Documentation records how aliases are maintained.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

## Next

Use alias-expanded source-context backtests to decide whether external context is mature enough for threshold policy approval.

