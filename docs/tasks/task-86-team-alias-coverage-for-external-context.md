# Task 86 - Team Alias Coverage For External Context

Status: in progress

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

## Implementation Notes

First slice implemented:

- Added `TeamAliasResolver` with exact canonical matching plus optional explicit aliases.
- Added `data/team_aliases.json` as the auditable local alias file. It starts empty until production unmatched teams are reviewed and mapped deliberately.
- `FeatureBuilder` now uses the resolver when selecting team history and when scoring whether the target team was home or away inside a historical match.
- Ambiguous aliases intentionally return only the direct canonical key, so they cannot silently enrich rows.
- Added read-only alias/enrichment coverage reporting:
  - API: `GET /api/live/enrichment-audit`
  - CLI: `python -m app.cli feature-enrichment-audit`
- Fixed Football-Data provenance detection to recognize both historical source labels currently present in code/tests: `football_data` and `football-data`.

Still open:

- Populate live Misli aliases with source/league/confidence metadata.
- Run before/after source-context backtests.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

## Next

Use alias-expanded source-context backtests to decide whether external context is mature enough for threshold policy approval.
