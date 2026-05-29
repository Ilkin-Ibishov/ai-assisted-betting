# Bet Ledger Dashboard Design

Date: 2026-05-29

## Goal

Add a dashboard view that shows upcoming betting opportunities and historical paper-bet performance in one auditable ledger. The user should be able to see each bet or candidate, its model probability of winning, the market-implied probability, the edge, whether the event is fresh or already played, and the eventual outcome and paper profit/loss.

## Decisions

- Use one unified ledger by default, not separate panels for candidates and paper bets.
- Show candidate recommendations and tracked paper bets together.
- Filter dates by match kickoff time, not recommendation creation time.
- Default filter is Fresh plus the next 7 days.
- Use a balanced result focus: keep fresh opportunities prominent while always showing result health, unresolved past matches, outcome, and paper P/L.
- Keep voided or unsafe historical rows available through filters, but do not let them look like current actionable bets.

## Ledger Row Types

Each row has a `row_type` and a `state`.

`row_type` values:

- `candidate`: recommendation that has not been logged as a paper bet.
- `tracked`: paper bet that is open or awaiting result.
- `resulted`: paper bet with a final outcome.
- `voided`: invalid, unsafe, cancelled, or explicitly voided paper bet.

`state` values:

- `fresh`: kickoff is in the future and the row is a candidate or tracked open bet.
- `needs_result`: kickoff is in the past and a tracked paper bet has no settlement or final result.
- `resulted`: settlement exists and the outcome is won, lost, pushed, or equivalent final state.
- `voided`: invalid, unsafe, cancelled, or explicitly voided.

## Backend Architecture

Add a server-side bet ledger API that merges recommendations and paper bets into one stable response model. Recommended endpoint:

`GET /api/live/bet-ledger`

Query parameters:

- `status`: `fresh`, `needs_result`, `resulted`, `voided`, or `all`.
- `date_range`: `today`, `tomorrow`, `next_7_days`, `last_7_days`, `last_30_days`, `custom`, or `all`.
- `from` and `to`: ISO dates used only when `date_range=custom`.
- `include_voided`: optional boolean for explicit unsafe/voided inclusion.

The backend owns the row classification logic so frontend behavior, tests, and future clients stay consistent.

## Ledger Response Shape

Each ledger row should include:

- identifiers: `id`, `row_type`, `paper_bet_id`, `recommendation_id`, `provider`, `run_id`.
- event data: `league`, `home_team`, `away_team`, `kickoff_at`, `market`, `selection`.
- price data: `odds`, `implied_probability`.
- model data: `model_probability`, `edge`, `expected_value`, `confidence_score`, `model_version`.
- status data: `state`, `status`, `is_valid_open`, `risk_flags`.
- result data: `outcome`, `settled_at`, `paper_profit_loss`, `closing_odds`, `clv`.
- audit data: `created_at`, `updated_at`, `source_snapshot_at`, `rationale`.

If a field is not available for a row type, return `null` rather than omitting it. This keeps the UI simple and makes missing data visible.

## UI Design

The dashboard should replace the current narrow open-paper-bets panel with a fuller Bet Ledger section.

Default controls:

- Status segmented control: Fresh, Needs result, Resulted, Voided, All.
- Date segmented control: Today, Tomorrow, 7 days, 30 days, Custom, All.
- Optional search/filter input for team or league.

Summary cards always visible:

- Fresh count.
- Tracked count.
- Needs result count.
- Resulted count.
- Paper P/L.
- Win rate.

Main table columns:

- Kickoff.
- Match.
- Pick.
- Model %.
- Implied %.
- Edge.
- Odds.
- State.
- Outcome.
- Paper P/L.

Row expansion should show rationale, risk flags, source snapshot time, model version, created time, CLV, settlement details, and raw status metadata. This keeps the main table readable while still supporting audit work.

## Business Rules

- Candidate rows are actionable only when kickoff is in the future and the recommendation passes existing gates.
- Tracked open paper bets are fresh only before kickoff.
- Past tracked paper bets without results must appear as `needs_result`.
- Resulted rows must emphasize `outcome` and `paper_profit_loss` in the main row.
- Voided and unsafe rows must not appear in the default Fresh view.
- The ledger should deduplicate candidates that already have matching paper bets. The paper bet row wins because it has the stronger audit trail.
- Kickoff time is the canonical date for filters. Created time is only shown in details.

## Error And Empty States

- If the ledger endpoint fails, show a clear inline error in the Bet Ledger section while keeping the rest of the dashboard usable.
- If Fresh has no rows, say that no fresh opportunities match the current filters and surface counts for Needs result and Resulted.
- If probability fields are missing, show `--` in the table and explain missing values in the expanded row when possible.
- If there are Needs result rows, show them as a visible audit queue rather than hiding them behind Resulted.

## Testing

Backend tests should cover:

- row classification for fresh, needs result, resulted, and voided rows.
- kickoff-date filtering.
- candidate/paper-bet deduplication.
- probability and P/L serialization.
- exclusion of unsafe or voided rows from the default Fresh view.

Frontend tests should cover:

- default Fresh plus next-7-days filter state.
- status and date filter changes.
- rendering candidate, tracked, needs-result, resulted, and voided rows.
- visible model probability, implied probability, edge, outcome, and paper P/L.
- empty and error states.

Browser verification should cover:

- desktop table readability.
- mobile behavior for the ledger section.
- filter interactions.
- row expansion.
- confirmation that no stale/unsafe paper bets appear as current actionable bets.

## Out Of Scope

- Real-money bet placement.
- New AI model integration.
- Automatic settlement from a new external results provider.
- Changing the existing recommendation gates except where needed to represent their output in the ledger.
