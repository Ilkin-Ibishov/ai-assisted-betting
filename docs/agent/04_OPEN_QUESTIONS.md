# Open Questions

Resolve these before or during the relevant implementation task.

## Live Recommendation Operations

Resolved direction: use a separate Railway worker service invoked by Railway cron or an equivalent scheduler. Keep the API and dashboard services with `LIVE_COLLECTION_ENABLED=false`; only the worker service uses `LIVE_COLLECTION_ENABLED=true`.

Open: choose an external alert destination, if any, after dashboard/API guardrail status is stable in staging. Task 61 added API/dashboard guardrail status but intentionally did not add notification bots.

## Outcome-Driven Threshold Policy

Resolved by Task 83: threshold proposals are persisted in `threshold_policy_runs`. Small samples stay advisory/fail-closed, loosening remains advisory by default, and active policy changes require explicit approval plus apply commands with rollback metadata.

## External Football Context Sources

Resolved by Task 84: Football-Data CSV is the first approved source. Open follow-up: add team alias coverage so Misli public team names can reliably match imported Football-Data historical rows.

## Release Process

Resolved direction: this is a solo-coder project and new Codex work should be pushed directly to `main` unless the user explicitly asks for a PR. Open follow-up: Task 85 must prove Railway deploys the pushed `main` commit before production success is claimed.

## Threshold Policy Operations

Open: decide whether dashboard policy approve/apply/rollback actions should be protected by a shared admin token, Railway-only access, or another lightweight operator guard. Do not add dashboard mutating controls until Task 87 defines governance and Task 88 implements protection.

## Documentation Maintenance

Resolved: after each implementation task, agents must update agent-context docs and relevant project docs before claiming completion. The canonical rule lives in:

```text
AGENTS.md
docs/agent/00_READ_ME_FIRST.md
docs/agent/03_DOC_READING_MAP.md
```

Resolved: after each implementation task, agents must include a concise completion report covering what was done, what is next, blockers, and technical debt or known limitations.

Resolved: after each implementation task, agents must run the full test suite and full lint check before claiming completion. Focused tests are useful during development but are not sufficient for final completion.

Resolved: technical debt must be tracked in `docs/agent/05_TECHNICAL_DEBT.md`, not only mentioned in chat responses.

## Schema Migrations

Resolved direction: use a lightweight SQLite migration registry for MVP instead of Alembic. Add Alembic later only if schema churn or non-SQLite support becomes significant.

## Command Names

Use `settle-results` everywhere. Older docs mention `settle-sample-results`; treat that as obsolete.

Keep `collect-matches` and `collect-odds` as CLI placeholders for future live/manual collection. They are not required for the first offline sample flow.

## Schema Clarifications

Resolved: `paper_bets.prediction_id` has a uniqueness rule so one prediction cannot create duplicate paper bets. Task 27 added migration `002_add_identity_unique_indexes` for older SQLite databases.

Resolved: `odds_snapshots` has an idempotency rule around:

```text
match_id, source, bookmaker, market, selection, snapshot_time
```

Task 27 added migration `002_add_identity_unique_indexes` for older SQLite databases.

For feature rows, treat `bookmaker_probability` as normalized bookmaker probability for MVP. Keep raw implied probability on `odds_snapshots.implied_probability`.

Do not add `completed_at` in the MVP unless it becomes necessary. Use `status = completed` and `kickoff_time < current_match.kickoff_time` for no-leakage feature generation.

## CLV

For MVP settlement, closing odds should be the latest odds snapshot for the same match, market, and selection where `is_closing = true`. If none exists, use the latest snapshot before kickoff and log a warning.

## Market Scope

Use `1X2` for the first sample pipeline. Structure settlement so `OVER_UNDER_2_5` can be added without rewriting the result settler.

## Football-Data Bookmakers

Use `B365` as the default Football-Data bookmaker for backward compatibility.

Use `ALL` to import every supported 1X2 bookmaker group present in a CSV. This can create multiple odds snapshots per match/selection at the same timestamp because `bookmaker` is part of the uniqueness rule.

Use Football-Data's aggregate columns as bookmaker names:

```text
Max
Avg
```

These are not real bookmakers; they are aggregate odds columns and should be interpreted as market summaries.

## Live Paper Loop

Resolved direction: Misli.az is the first localized provider candidate for Tasks 38-40 because the user lives in Azerbaijan and wants local real-time paper odds. Discovery must stay public, unauthenticated, and robots.txt-aware. Public rendered football odds are available through `tools/misli-public-snapshot.mjs`; do not expand this into login, protected path scraping, CAPTCHA/bot bypass, proxy evasion, or real betting.

Resolved direction: Task 38 must model Misli as a public snapshot source with typed DTOs and fail-closed validation. Task 40 may import Misli only after full kickoff datetime and complete 1X2 odds validation pass; otherwise it should keep a deterministic fake/manual provider path.

Resolved direction: Task 69 resolves bare Misli `HH:MM` rows to the snapshot `scraped_at` local date while still failing closed when the scrape timestamp is missing or invalid. Stronger date group extraction from rendered page headers remains technical debt, not an open product decision.

Resolved direction: live run registry uses a single SQLite `live_runs` table for MVP. Split detailed errors into a child table only if Task 40 or dashboard monitoring needs more than `errors_count` and `error_summary`.

Resolved direction: do not add scheduling immediately after Task 45. The deterministic manual dry run is repeatable, but `run-live-paper-cycle` still processes all scheduled matches in the active database. Resolve run scoping before scheduling.
