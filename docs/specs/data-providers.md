# 05 — Data Providers

## Principle

The core engine must not know whether data comes from live API, CSV, sample data, or historical replay.

Use provider interfaces.

## Base Interfaces

Create:

```text
app/providers/base.py
```

Suggested interfaces:

```python
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Iterable, Optional

from app.schemas.match import RawMatch
from app.schemas.odds import RawOddsSnapshot
from app.schemas.result import RawResult


class MatchProvider(ABC):
    @abstractmethod
    def get_matches(self, start_time: datetime, end_time: datetime) -> Iterable[RawMatch]:
        pass


class OddsProvider(ABC):
    @abstractmethod
    def get_odds(self, match_source_id: str, market: str) -> Iterable[RawOddsSnapshot]:
        pass


class ResultProvider(ABC):
    @abstractmethod
    def get_result(self, match_source_id: str) -> Optional[RawResult]:
        pass
```

## Provider Types

### 1. SampleProvider

Purpose:

- Local deterministic testing
- No network calls
- Small built-in sample data

Use first.

### 2. ManualCSVProvider

Purpose:

- Import user-provided CSV files
- Useful before live API integration

### 3. HistoricalCSVProvider

Purpose:

- Import historical football datasets
- Later used for replay/backtesting

### FootballDataCsvProvider

Purpose:

- Import public Football-Data.co.uk CSV files.
- Support local files and direct public CSV URLs.
- Normalize historical results and 1X2 odds into the same database tables as the sample provider.

Supported MVP bookmaker groups:

```text
B365
BW
IW
PS
WH
VC
Max
Avg
```

Default bookmaker:

```text
B365
```

Use:

```text
ALL
```

to import all supported bookmaker groups present in the file.

### 4. LiveAPIProvider

Purpose:

- Future API-based collection
- Must use permitted/public/official data sources

### Misli.az Candidate

Misli.az is the first localized live provider candidate for the paper-only live loop.

Allowed discovery:

```text
public pages
unauthenticated network calls visible from public pages
robots.txt allowed paths
low-rate collection
```

Blocked:

```text
login automation
account pages
protected live-bet detail routes
CAPTCHA or bot-protection bypass
proxy/stealth evasion
real bet placement
```

If public allowed odds cannot be collected reliably, use a deterministic fake/manual provider for the first live-loop implementation.

Current discovery artifact:

```text
docs/research/misli-public-discovery.md
tools/misli-public-snapshot.mjs
```

The prototype collects public football rows through Playwright and emits JSON only. It does not log in, bypass protections, place bets, or write to SQLite.

Typed contract support:

```text
app/providers/base.py
app/providers/misli_public.py
```

Misli snapshot DTO validation fails closed unless full kickoff date/time, non-empty event identity/team/league fields, raw row text, and complete HOME/DRAW/AWAY 1X2 odds are present. Task 53 also normalizes comma decimal odds such as `2,16`.

Task 53 snapshot hardening:

```text
empty snapshots -> live-run error: possible Misli parser drift
row-count mismatch / all rows skipped -> live-run error: low extraction confidence
provider-health analysis -> explicit parser drift, stale snapshot, and low-confidence risk flags
```

### 5. ReplayProvider

Purpose:

- Replays historical snapshots through the same core engine
- Used for backtesting-like evaluation

## Provider Output Rules

Providers return raw objects.

Normalizers convert raw objects into internal DB-ready data.

Do not let providers write directly into the database.

Correct:

```text
Provider -> Raw Schema -> Normalizer -> Repository -> DB
```

Incorrect:

```text
Provider -> DB directly
```

## Snapshot Timing

For live paper betting, store snapshots at approximate intervals:

```text
T-48h
T-24h
T-12h
T-6h
T-1h
kickoff
```

Do not require exact timing in MVP.

Store actual timestamp and computed `minutes_before_kickoff`.

## Odds Validation Rules

Reject odds if:

```text
odds_decimal <= 1.0
odds_decimal is null
market unsupported
selection unsupported
match_id missing
snapshot_time missing
```

## Team Name Normalization

Use normalized names internally.

Example:

```text
Manchester United
Man United
Man Utd
```

should map to one canonical value.

MVP can use exact names only, but code must have a place for mapping.

Create:

```text
data/team_aliases.json
```

later.

## Live Collection Warning

Do not implement anti-bot bypass.

If a live bookmaker page is protected, skip it for MVP.

Use official/public/allowed sources.

For the paper-only live loop roadmap, read:

```text
docs/specs/live-paper-loop.md
docs/tasks/task-38-live-provider-contract.md
```
