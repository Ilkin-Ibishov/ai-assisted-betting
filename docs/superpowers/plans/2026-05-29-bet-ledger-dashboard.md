# Bet Ledger Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a unified dashboard ledger that shows fresh candidate recommendations, tracked paper bets, unresolved past bets, resulted bets, probabilities, edge, outcome, and paper P/L.

**Architecture:** Add a backend `BetLedgerService` that merges `PaperRecommendation` and `PaperBet` rows into one stable API model, then consume that model directly in the React dashboard. Keep row classification server-side; keep frontend helper logic limited to display filtering, summary metrics, and formatting.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, React, TanStack Query, Vitest, Tailwind CSS, lucide-react, Playwright/browser verification.

---

## File Structure

- Create `app/services/bet_ledger_service.py`: query recommendations, paper bets, predictions, and matches; classify rows; apply kickoff-date filters; serialize the ledger response.
- Modify `app/api.py`: register `GET /api/live/bet-ledger` and call `BetLedgerService`.
- Modify `tests/unit/test_dashboard_api.py`: add endpoint-level tests using existing seeded SQLite fixtures.
- Create `tests/unit/test_bet_ledger_service.py`: focused service tests for classification, date filters, deduplication, and unsafe exclusion.
- Modify `dashboard/src/lib/api.ts`: add `BetLedgerRow`, `BetLedgerSummary`, `BetLedgerResponse`, query types, and `fetchBetLedger`.
- Create `dashboard/src/lib/bet-ledger.ts`: frontend display helpers for summary cards, row labels, row tones, and default query state.
- Create `dashboard/src/lib/bet-ledger.test.ts`: Vitest coverage for frontend helper behavior.
- Create `dashboard/src/components/dashboard/bet-ledger-panel.tsx`: dashboard section with filters, summary cards, table, row details, loading, error, and empty states.
- Modify `dashboard/src/App.tsx`: fetch the ledger, pass it to the dashboard content, replace `OpenPaperBetsPanel` with `BetLedgerPanel`, and remove unused paper-bet grouping UI if no longer referenced.

---

### Task 1: Backend Ledger Service Tests

**Files:**
- Create: `tests/unit/test_bet_ledger_service.py`
- Read: `app/db/models.py`
- Read: `app/db/repositories.py`

- [ ] **Step 1: Write service tests for row classification**

Create `tests/unit/test_bet_ledger_service.py` with these imports and helper structure:

```python
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import text

from app.db.engine import create_engine_from_url, session_scope
from app.db.models import Base, PaperRecommendation
from app.db.repositories import MatchRepository, PaperBetRepository, PredictionRepository
from app.services.bet_ledger_service import BetLedgerService
```

Add this database helper:

```python
def create_database(tmp_path: Path) -> str:
    database_url = f"sqlite:///{tmp_path / 'ledger.db'}"
    engine = create_engine_from_url(database_url)
    Base.metadata.create_all(engine)
    engine.dispose()
    return database_url
```

Add this seed helper:

```python
def seed_prediction_and_bet(
    database_url: str,
    *,
    source_match_id: str,
    kickoff_time: str,
    selection: str,
    status: str = "open",
    expected_value: float = 0.12,
    profit_loss_units: float | None = None,
    settled_at: str | None = None,
    confidence_score: float | None = 0.7,
) -> None:
    engine = create_engine_from_url(database_url)
    with session_scope(engine) as session:
        match = MatchRepository(session).add(
            source="misli_public",
            source_match_id=source_match_id,
            league="Sample Premier",
            home_team=f"Home {source_match_id}",
            away_team=f"Away {source_match_id}",
            kickoff_time=kickoff_time,
        )
        prediction = PredictionRepository(session).add(
            match_id=match.id,
            market="1X2",
            selection=selection,
            model_name="baseline_heuristic",
            model_version="v0",
            model_probability=0.58,
            bookmaker_probability=0.42,
            edge=0.16,
            confidence_score=confidence_score,
            decision="BET",
            reason="seed bet",
        )
        bet = PaperBetRepository(session).add(
            prediction_id=prediction.id,
            match_id=match.id,
            market="1X2",
            selection=selection,
            odds_taken=2.4,
            stake_units=1.0,
            expected_value=expected_value,
            status=status,
        )
        bet.profit_loss_units = profit_loss_units
        bet.settled_at = settled_at
    engine.dispose()
```

Add this recommendation helper:

```python
def seed_recommendation(
    database_url: str,
    *,
    source_match_id: str,
    kickoff_time: str,
    selection: str = "HOME",
    prediction_id: int | None = None,
    status: str = "active",
    grade: str = "recommended",
    risk_flags: str = '["no_current_risk_flags"]',
) -> None:
    engine = create_engine_from_url(database_url)
    with session_scope(engine) as session:
        match = MatchRepository(session).add(
            source="misli_public",
            source_match_id=source_match_id,
            league="Sample Premier",
            home_team=f"Home {source_match_id}",
            away_team=f"Away {source_match_id}",
            kickoff_time=kickoff_time,
        )
        session.add(
            PaperRecommendation(
                match_id=match.id,
                prediction_id=prediction_id,
                source_match_id=source_match_id,
                bookmaker="Misli.az",
                market="1X2",
                selection=selection,
                latest_snapshot_time="2026-05-29T08:00:00+00:00",
                model_name="baseline_heuristic",
                model_version="v0",
                grade=grade,
                status=status,
                model_probability=0.61,
                implied_probability=0.45,
                edge=0.16,
                confidence_score=0.73,
                current_odds=2.22,
                expected_value=0.35,
                risk_flags_json=risk_flags,
                rationale="Positive edge is above the recommendation gate.",
            )
        )
    engine.dispose()
```

Add tests:

```python
def test_ledger_classifies_fresh_candidate_and_tracked_bet(tmp_path: Path) -> None:
    database_url = create_database(tmp_path)
    seed_recommendation(
        database_url,
        source_match_id="candidate-future",
        kickoff_time="2026-05-30T20:30:00+04:00",
    )
    seed_prediction_and_bet(
        database_url,
        source_match_id="tracked-future",
        kickoff_time="2026-05-31T20:30:00+04:00",
        selection="AWAY",
    )

    payload = BetLedgerService(database_url).ledger(
        status="fresh",
        date_range="next_7_days",
        now=datetime(2026, 5, 29, 8, 0, tzinfo=UTC),
    )

    assert payload["summary"]["fresh_count"] == 2
    assert [row["row_type"] for row in payload["rows"]] == ["candidate", "tracked"]
    assert {row["state"] for row in payload["rows"]} == {"fresh"}
    assert payload["rows"][0]["model_probability"] is not None
    assert payload["rows"][0]["implied_probability"] is not None
```

```python
def test_ledger_surfaces_needs_result_and_resulted_rows(tmp_path: Path) -> None:
    database_url = create_database(tmp_path)
    seed_prediction_and_bet(
        database_url,
        source_match_id="past-open",
        kickoff_time="2026-05-28T20:30:00+04:00",
        selection="HOME",
    )
    seed_prediction_and_bet(
        database_url,
        source_match_id="past-won",
        kickoff_time="2026-05-27T20:30:00+04:00",
        selection="AWAY",
        status="won",
        profit_loss_units=1.4,
        settled_at="2026-05-27T23:00:00+00:00",
    )

    payload = BetLedgerService(database_url).ledger(
        status="all",
        date_range="last_7_days",
        now=datetime(2026, 5, 29, 8, 0, tzinfo=UTC),
    )

    rows_by_match = {row["source_match_id"]: row for row in payload["rows"]}
    assert rows_by_match["past-open"]["state"] == "needs_result"
    assert rows_by_match["past-open"]["outcome"] is None
    assert rows_by_match["past-won"]["state"] == "resulted"
    assert rows_by_match["past-won"]["outcome"] == "won"
    assert rows_by_match["past-won"]["paper_profit_loss"] == 1.4
```

```python
def test_ledger_excludes_voided_from_default_fresh_view(tmp_path: Path) -> None:
    database_url = create_database(tmp_path)
    seed_prediction_and_bet(
        database_url,
        source_match_id="voided",
        kickoff_time="2026-05-30T20:30:00+04:00",
        selection="HOME",
        status="void",
        profit_loss_units=0.0,
        settled_at="2026-05-29T09:00:00+00:00",
    )

    fresh = BetLedgerService(database_url).ledger(
        status="fresh",
        date_range="next_7_days",
        now=datetime(2026, 5, 29, 8, 0, tzinfo=UTC),
    )
    all_rows = BetLedgerService(database_url).ledger(
        status="all",
        date_range="next_7_days",
        include_voided=True,
        now=datetime(2026, 5, 29, 8, 0, tzinfo=UTC),
    )

    assert fresh["rows"] == []
    assert all_rows["rows"][0]["state"] == "voided"
```

```python
def test_ledger_deduplicates_candidate_when_matching_paper_bet_exists(tmp_path: Path) -> None:
    database_url = create_database(tmp_path)
    seed_prediction_and_bet(
        database_url,
        source_match_id="same-match",
        kickoff_time="2026-05-30T20:30:00+04:00",
        selection="HOME",
    )
    engine = create_engine_from_url(database_url)
    with session_scope(engine) as session:
        prediction_id = session.execute(text("SELECT id FROM predictions LIMIT 1")).scalar_one()
    engine.dispose()
    seed_recommendation(
        database_url,
        source_match_id="same-match",
        kickoff_time="2026-05-30T20:30:00+04:00",
        selection="HOME",
        prediction_id=prediction_id,
    )

    payload = BetLedgerService(database_url).ledger(
        status="fresh",
        date_range="next_7_days",
        now=datetime(2026, 5, 29, 8, 0, tzinfo=UTC),
    )

    assert len(payload["rows"]) == 1
    assert payload["rows"][0]["row_type"] == "tracked"
    assert payload["rows"][0]["paper_bet_id"] is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/unit/test_bet_ledger_service.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.bet_ledger_service'`.

---

### Task 2: Backend Ledger Service Implementation

**Files:**
- Create: `app/services/bet_ledger_service.py`
- Test: `tests/unit/test_bet_ledger_service.py`

- [ ] **Step 1: Implement the service skeleton and public API**

Create `app/services/bet_ledger_service.py`:

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any, Literal

from sqlalchemy import select

from app.db.engine import create_engine_from_url, session_scope
from app.db.models import Match, PaperBet, PaperRecommendation, Prediction

LedgerStatus = Literal["fresh", "needs_result", "resulted", "voided", "all"]
DateRange = Literal[
    "today",
    "tomorrow",
    "next_7_days",
    "last_7_days",
    "last_30_days",
    "custom",
    "all",
]


@dataclass(frozen=True)
class DateWindow:
    start: datetime | None
    end: datetime | None


class BetLedgerService:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def ledger(
        self,
        *,
        status: LedgerStatus = "fresh",
        date_range: DateRange = "next_7_days",
        from_date: str | None = None,
        to_date: str | None = None,
        include_voided: bool = False,
        limit: int = 500,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        reference_time = now or datetime.now(UTC)
        window = _date_window(date_range, from_date=from_date, to_date=to_date, now=reference_time)
        engine = create_engine_from_url(self.database_url)
        try:
            with session_scope(engine) as session:
                paper_rows = session.execute(
                    select(PaperBet, Prediction, Match)
                    .join(Prediction, PaperBet.prediction_id == Prediction.id)
                    .join(Match, PaperBet.match_id == Match.id)
                    .order_by(Match.kickoff_time.asc(), PaperBet.id.asc())
                ).all()
                recommendation_rows = session.execute(
                    select(PaperRecommendation, Match)
                    .join(Match, PaperRecommendation.match_id == Match.id)
                    .order_by(Match.kickoff_time.asc(), PaperRecommendation.id.asc())
                ).all()
                rows = _build_rows(
                    paper_rows=paper_rows,
                    recommendation_rows=recommendation_rows,
                    status=status,
                    window=window,
                    include_voided=include_voided,
                    limit=max(1, min(limit, 500)),
                    now=reference_time,
                )
                return {"summary": _summary(rows), "rows": rows}
        finally:
            engine.dispose()
```

- [ ] **Step 2: Add row builders and filtering**

Append:

```python
def _build_rows(
    *,
    paper_rows: list[tuple[PaperBet, Prediction, Match]],
    recommendation_rows: list[tuple[PaperRecommendation, Match]],
    status: LedgerStatus,
    window: DateWindow,
    include_voided: bool,
    limit: int,
    now: datetime,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    tracked_keys: set[tuple[int, str, str]] = set()

    for paper_bet, prediction, match in paper_rows:
        tracked_keys.add((paper_bet.match_id, paper_bet.market, paper_bet.selection))
        row = _paper_bet_row(paper_bet, prediction, match, now=now)
        if _row_matches(row, status=status, window=window, include_voided=include_voided):
            rows.append(row)

    for recommendation, match in recommendation_rows:
        key = (recommendation.match_id, recommendation.market, recommendation.selection)
        if key in tracked_keys:
            continue
        row = _recommendation_row(recommendation, match, now=now)
        if _row_matches(row, status=status, window=window, include_voided=include_voided):
            rows.append(row)

    rows.sort(key=lambda row: (row["kickoff_at"] or "", row["row_type"], row["id"]))
    return rows[:limit]


def _row_matches(
    row: dict[str, Any],
    *,
    status: LedgerStatus,
    window: DateWindow,
    include_voided: bool,
) -> bool:
    if row["state"] == "voided" and not include_voided and status != "voided":
        return False
    if status != "all" and row["state"] != status:
        return False
    kickoff = _parse_iso_datetime(row["kickoff_at"])
    if kickoff is None:
        return False
    if window.start is not None and kickoff < window.start:
        return False
    if window.end is not None and kickoff >= window.end:
        return False
    return True
```

- [ ] **Step 3: Add row serializers**

Append:

```python
def _paper_bet_row(
    paper_bet: PaperBet,
    prediction: Prediction,
    match: Match,
    *,
    now: datetime,
) -> dict[str, Any]:
    state = _paper_bet_state(paper_bet, match, now=now)
    risk_flags = _paper_bet_risk_flags(paper_bet, prediction, match, now=now)
    return {
        "id": f"paper-bet-{paper_bet.id}",
        "row_type": "resulted" if state == "resulted" else "voided" if state == "voided" else "tracked",
        "paper_bet_id": paper_bet.id,
        "recommendation_id": None,
        "prediction_id": paper_bet.prediction_id,
        "provider": match.source,
        "run_id": None,
        "source_match_id": match.source_match_id,
        "league": match.league,
        "home_team": match.home_team,
        "away_team": match.away_team,
        "match_label": f"{match.home_team} vs {match.away_team}",
        "kickoff_at": match.kickoff_time,
        "market": paper_bet.market,
        "selection": paper_bet.selection,
        "odds": paper_bet.odds_taken,
        "implied_probability": prediction.bookmaker_probability,
        "model_probability": prediction.model_probability,
        "edge": prediction.edge,
        "expected_value": paper_bet.expected_value,
        "confidence_score": prediction.confidence_score,
        "model_name": prediction.model_name,
        "model_version": prediction.model_version,
        "state": state,
        "status": paper_bet.status,
        "is_valid_open": paper_bet.status == "open" and risk_flags == ["no_current_risk_flags"],
        "risk_flags": risk_flags,
        "outcome": paper_bet.status if state in {"resulted", "voided"} else None,
        "settled_at": paper_bet.settled_at,
        "paper_profit_loss": paper_bet.profit_loss_units,
        "closing_odds": paper_bet.closing_odds,
        "clv": paper_bet.clv,
        "created_at": paper_bet.created_at,
        "updated_at": None,
        "source_snapshot_at": None,
        "rationale": prediction.reason,
    }


def _recommendation_row(
    recommendation: PaperRecommendation,
    match: Match,
    *,
    now: datetime,
) -> dict[str, Any]:
    state = "fresh" if _is_future(match.kickoff_time, now=now) else "needs_result"
    return {
        "id": f"recommendation-{recommendation.id}",
        "row_type": "candidate",
        "paper_bet_id": None,
        "recommendation_id": recommendation.id,
        "prediction_id": recommendation.prediction_id,
        "provider": match.source,
        "run_id": recommendation.source_run_id,
        "source_match_id": recommendation.source_match_id,
        "league": match.league,
        "home_team": match.home_team,
        "away_team": match.away_team,
        "match_label": f"{match.home_team} vs {match.away_team}",
        "kickoff_at": match.kickoff_time,
        "market": recommendation.market,
        "selection": recommendation.selection,
        "odds": recommendation.current_odds,
        "implied_probability": recommendation.implied_probability,
        "model_probability": recommendation.model_probability,
        "edge": recommendation.edge,
        "expected_value": recommendation.expected_value,
        "confidence_score": recommendation.confidence_score,
        "model_name": recommendation.model_name,
        "model_version": recommendation.model_version,
        "state": state,
        "status": recommendation.status,
        "is_valid_open": state == "fresh" and recommendation.status == "active",
        "risk_flags": json.loads(recommendation.risk_flags_json),
        "outcome": None,
        "settled_at": None,
        "paper_profit_loss": None,
        "closing_odds": None,
        "clv": None,
        "created_at": recommendation.created_at,
        "updated_at": None,
        "source_snapshot_at": recommendation.latest_snapshot_time,
        "rationale": recommendation.rationale,
    }
```

- [ ] **Step 4: Add state, date, and summary helpers**

Append:

```python
def _paper_bet_state(paper_bet: PaperBet, match: Match, *, now: datetime) -> str:
    if paper_bet.status in {"void", "voided", "cancelled", "canceled"}:
        return "voided"
    if paper_bet.status != "open":
        return "resulted"
    return "fresh" if _is_future(match.kickoff_time, now=now) else "needs_result"


def _paper_bet_risk_flags(
    paper_bet: PaperBet,
    prediction: Prediction,
    match: Match,
    *,
    now: datetime,
) -> list[str]:
    flags: list[str] = []
    if paper_bet.status != "open":
        flags.append(f"status_{paper_bet.status}")
    if paper_bet.expected_value <= 0:
        flags.append("negative_expected_value")
    if prediction.confidence_score is not None and prediction.confidence_score < 0.5:
        flags.append("low_confidence")
    kickoff = _parse_iso_datetime(match.kickoff_time)
    if paper_bet.status == "open" and kickoff is not None and kickoff <= now:
        flags.append("past_kickoff_open")
    return flags or ["no_current_risk_flags"]


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    resulted = [row for row in rows if row["state"] == "resulted"]
    wins = [row for row in resulted if row["outcome"] == "won"]
    profit_loss = sum(row["paper_profit_loss"] or 0 for row in resulted)
    return {
        "fresh_count": sum(1 for row in rows if row["state"] == "fresh"),
        "tracked_count": sum(1 for row in rows if row["row_type"] == "tracked"),
        "needs_result_count": sum(1 for row in rows if row["state"] == "needs_result"),
        "resulted_count": len(resulted),
        "voided_count": sum(1 for row in rows if row["state"] == "voided"),
        "paper_profit_loss": round(profit_loss, 6),
        "win_rate": round(len(wins) / len(resulted), 6) if resulted else None,
    }


def _date_window(
    date_range: DateRange,
    *,
    from_date: str | None,
    to_date: str | None,
    now: datetime,
) -> DateWindow:
    today = now.astimezone(UTC).date()
    if date_range == "all":
        return DateWindow(None, None)
    if date_range == "today":
        return _day_window(today)
    if date_range == "tomorrow":
        return _day_window(today + timedelta(days=1))
    if date_range == "next_7_days":
        return DateWindow(_start_of_day(today), _start_of_day(today + timedelta(days=8)))
    if date_range == "last_7_days":
        return DateWindow(_start_of_day(today - timedelta(days=7)), _start_of_day(today + timedelta(days=1)))
    if date_range == "last_30_days":
        return DateWindow(_start_of_day(today - timedelta(days=30)), _start_of_day(today + timedelta(days=1)))
    if date_range == "custom":
        return DateWindow(_parse_date_start(from_date), _parse_date_end(to_date))
    return DateWindow(_start_of_day(today), _start_of_day(today + timedelta(days=8)))


def _day_window(day: date) -> DateWindow:
    return DateWindow(_start_of_day(day), _start_of_day(day + timedelta(days=1)))


def _start_of_day(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=UTC)


def _parse_date_start(value: str | None) -> datetime | None:
    return _start_of_day(date.fromisoformat(value)) if value else None


def _parse_date_end(value: str | None) -> datetime | None:
    return _start_of_day(date.fromisoformat(value) + timedelta(days=1)) if value else None


def _is_future(value: str, *, now: datetime) -> bool:
    kickoff = _parse_iso_datetime(value)
    return kickoff is not None and kickoff > now


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
```

- [ ] **Step 5: Run service tests**

Run:

```bash
pytest tests/unit/test_bet_ledger_service.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit backend service**

Run:

```bash
git add app/services/bet_ledger_service.py tests/unit/test_bet_ledger_service.py
git commit -m "feat: add bet ledger service"
```

---

### Task 3: Backend API Endpoint

**Files:**
- Modify: `app/api.py`
- Modify: `tests/unit/test_dashboard_api.py`
- Test: `tests/unit/test_dashboard_api.py`

- [ ] **Step 1: Write endpoint tests**

Add this test near the existing live recommendation and paper-bet endpoint tests:

```python
def test_live_bet_ledger_endpoint_returns_default_fresh_rows(tmp_path: Path) -> None:
    database_url = _create_live_api_database(tmp_path)
    _seed_recommendation_database(database_url)
    _seed_live_status_database(database_url)
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    response = client.get(
        "/api/live/bet-ledger",
        params={
            "status": "fresh",
            "date_range": "next_7_days",
            "now": "2026-05-18T08:00:00+00:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "summary" in payload
    assert "rows" in payload
    assert payload["summary"]["fresh_count"] >= 1
    assert {row["state"] for row in payload["rows"]} == {"fresh"}
    assert {"model_probability", "implied_probability", "edge", "paper_profit_loss"}.issubset(
        payload["rows"][0].keys()
    )
```

Add this test:

```python
def test_live_bet_ledger_endpoint_can_show_resulted_rows(tmp_path: Path) -> None:
    database_url = _create_live_api_database(tmp_path)
    _seed_live_status_database(database_url)
    client = TestClient(create_api(reports_dir=tmp_path / "reports", database_url=database_url))

    response = client.get(
        "/api/live/bet-ledger",
        params={
            "status": "resulted",
            "date_range": "all",
            "now": "2026-06-20T08:00:00+00:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["resulted_count"] == 1
    assert payload["rows"][0]["outcome"] == "won"
```

- [ ] **Step 2: Run endpoint tests to verify they fail**

Run:

```bash
pytest tests/unit/test_dashboard_api.py::test_live_bet_ledger_endpoint_returns_default_fresh_rows tests/unit/test_dashboard_api.py::test_live_bet_ledger_endpoint_can_show_resulted_rows -v
```

Expected: FAIL with HTTP 404 for `/api/live/bet-ledger`.

- [ ] **Step 3: Wire the endpoint**

In `app/api.py`, add the import:

```python
from app.services.bet_ledger_service import BetLedgerService
```

Inside `create_api`, after `list_live_paper_bets`, add:

```python
    @api.get("/api/live/bet-ledger")
    def get_live_bet_ledger(
        status: str = "fresh",
        date_range: str = "next_7_days",
        from_date: str | None = None,
        to_date: str | None = None,
        include_voided: bool = False,
        limit: int = 500,
        now: str | None = None,
    ) -> dict[str, Any]:
        reference_time = _parse_iso_datetime(now) if now else None
        return BetLedgerService(live_database_url).ledger(
            status=status,  # type: ignore[arg-type]
            date_range=date_range,  # type: ignore[arg-type]
            from_date=from_date,
            to_date=to_date,
            include_voided=include_voided,
            limit=limit,
            now=reference_time,
        )
```

- [ ] **Step 4: Run endpoint tests**

Run:

```bash
pytest tests/unit/test_dashboard_api.py::test_live_bet_ledger_endpoint_returns_default_fresh_rows tests/unit/test_dashboard_api.py::test_live_bet_ledger_endpoint_can_show_resulted_rows -v
```

Expected: PASS.

- [ ] **Step 5: Run related backend tests**

Run:

```bash
pytest tests/unit/test_bet_ledger_service.py tests/unit/test_dashboard_api.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit API endpoint**

Run:

```bash
git add app/api.py tests/unit/test_dashboard_api.py
git commit -m "feat: expose live bet ledger endpoint"
```

---

### Task 4: Frontend API Types And Fetcher

**Files:**
- Modify: `dashboard/src/lib/api.ts`
- Modify: `dashboard/src/lib/api.test.ts`

- [ ] **Step 1: Add fetcher tests**

In `dashboard/src/lib/api.test.ts`, add:

```typescript
import { buildApiUrl, fetchBetLedger } from '@/lib/api'
```

If the file already imports from `@/lib/api`, extend that import rather than duplicating it.

Add this test:

```typescript
it('fetches bet ledger with status and date filters', async () => {
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
    ok: true,
    json: async () => ({
      summary: {
        fresh_count: 1,
        tracked_count: 0,
        needs_result_count: 0,
        resulted_count: 0,
        voided_count: 0,
        paper_profit_loss: 0,
        win_rate: null,
      },
      rows: [],
    }),
  } as Response)

  await fetchBetLedger({ status: 'fresh', dateRange: 'next_7_days' })

  expect(fetchMock).toHaveBeenCalledWith(
    buildApiUrl('/api/live/bet-ledger?status=fresh&date_range=next_7_days'),
  )
})
```

- [ ] **Step 2: Run frontend API test to verify it fails**

Run:

```bash
cd dashboard
npm test -- src/lib/api.test.ts
```

Expected: FAIL because `fetchBetLedger` is not exported.

- [ ] **Step 3: Add API types and fetcher**

In `dashboard/src/lib/api.ts`, add:

```typescript
export type BetLedgerStatus = 'fresh' | 'needs_result' | 'resulted' | 'voided' | 'all'

export type BetLedgerDateRange =
  | 'today'
  | 'tomorrow'
  | 'next_7_days'
  | 'last_7_days'
  | 'last_30_days'
  | 'custom'
  | 'all'

export type BetLedgerSummary = {
  fresh_count: number
  tracked_count: number
  needs_result_count: number
  resulted_count: number
  voided_count: number
  paper_profit_loss: number
  win_rate: number | null
}

export type BetLedgerRow = {
  id: string
  row_type: 'candidate' | 'tracked' | 'resulted' | 'voided'
  paper_bet_id: number | null
  recommendation_id: number | null
  prediction_id: number | null
  provider: string | null
  run_id: string | null
  source_match_id: string
  league: string
  home_team: string
  away_team: string
  match_label: string
  kickoff_at: string
  market: string
  selection: string
  odds: number | null
  implied_probability: number | null
  model_probability: number | null
  edge: number | null
  expected_value: number | null
  confidence_score: number | null
  model_name: string | null
  model_version: string | null
  state: BetLedgerStatus
  status: string
  is_valid_open: boolean
  risk_flags: string[]
  outcome: string | null
  settled_at: string | null
  paper_profit_loss: number | null
  closing_odds: number | null
  clv: number | null
  created_at: string
  updated_at: string | null
  source_snapshot_at: string | null
  rationale: string | null
}

export type BetLedgerResponse = {
  summary: BetLedgerSummary
  rows: BetLedgerRow[]
}

export type BetLedgerQuery = {
  status?: BetLedgerStatus
  dateRange?: BetLedgerDateRange
  from?: string
  to?: string
  includeVoided?: boolean
}
```

Add this fetcher:

```typescript
export async function fetchBetLedger(query: BetLedgerQuery = {}): Promise<BetLedgerResponse> {
  const params = new URLSearchParams()
  params.set('status', query.status ?? 'fresh')
  params.set('date_range', query.dateRange ?? 'next_7_days')
  if (query.from) params.set('from_date', query.from)
  if (query.to) params.set('to_date', query.to)
  if (query.includeVoided) params.set('include_voided', 'true')

  return getJson(`/api/live/bet-ledger?${params.toString()}`)
}
```

- [ ] **Step 4: Run frontend API test**

Run:

```bash
cd dashboard
npm test -- src/lib/api.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit frontend API types**

Run:

```bash
git add dashboard/src/lib/api.ts dashboard/src/lib/api.test.ts
git commit -m "feat: add bet ledger dashboard api client"
```

---

### Task 5: Frontend Ledger Helpers

**Files:**
- Create: `dashboard/src/lib/bet-ledger.ts`
- Create: `dashboard/src/lib/bet-ledger.test.ts`

- [ ] **Step 1: Write helper tests**

Create `dashboard/src/lib/bet-ledger.test.ts`:

```typescript
import { describe, expect, it } from 'vitest'
import type { BetLedgerRow } from '@/lib/api'
import {
  betLedgerDefaultQuery,
  betLedgerStateLabel,
  betLedgerStateTone,
  buildBetLedgerDisplaySummary,
} from '@/lib/bet-ledger'

describe('bet ledger helpers', () => {
  it('uses Fresh plus next 7 days by default', () => {
    expect(betLedgerDefaultQuery).toEqual({ status: 'fresh', dateRange: 'next_7_days' })
  })

  it('builds display summary from backend summary and rows', () => {
    const summary = buildBetLedgerDisplaySummary({
      summary: {
        fresh_count: 2,
        tracked_count: 1,
        needs_result_count: 1,
        resulted_count: 3,
        voided_count: 1,
        paper_profit_loss: 2.4,
        win_rate: 0.667,
      },
      rows: [row({ state: 'fresh' }), row({ state: 'needs_result' })],
    })

    expect(summary.cards.map((card) => card.label)).toEqual([
      'Fresh',
      'Tracked',
      'Needs result',
      'Resulted',
      'Paper P/L',
      'Win rate',
    ])
    expect(summary.cards[4].value).toBe('+2.4u')
    expect(summary.cards[5].value).toBe('66.7%')
  })

  it('labels row states for compact UI display', () => {
    expect(betLedgerStateLabel('needs_result')).toBe('Needs result')
    expect(betLedgerStateTone('needs_result')).toBe('warning')
    expect(betLedgerStateTone('voided')).toBe('muted')
  })
})

function row(overrides: Partial<BetLedgerRow>): BetLedgerRow {
  return {
    id: 'recommendation-1',
    row_type: 'candidate',
    paper_bet_id: null,
    recommendation_id: 1,
    prediction_id: null,
    provider: 'misli_public',
    run_id: null,
    source_match_id: 'match-1',
    league: 'Sample Premier',
    home_team: 'Home',
    away_team: 'Away',
    match_label: 'Home vs Away',
    kickoff_at: '2026-05-30T20:30:00+04:00',
    market: '1X2',
    selection: 'HOME',
    odds: 2.2,
    implied_probability: 0.45,
    model_probability: 0.61,
    edge: 0.16,
    expected_value: 0.35,
    confidence_score: 0.7,
    model_name: 'baseline_heuristic',
    model_version: 'v0',
    state: 'fresh',
    status: 'active',
    is_valid_open: true,
    risk_flags: ['no_current_risk_flags'],
    outcome: null,
    settled_at: null,
    paper_profit_loss: null,
    closing_odds: null,
    clv: null,
    created_at: '2026-05-29T08:00:00+00:00',
    updated_at: null,
    source_snapshot_at: '2026-05-29T08:00:00+00:00',
    rationale: 'Positive edge.',
    ...overrides,
  }
}
```

- [ ] **Step 2: Run helper tests to verify they fail**

Run:

```bash
cd dashboard
npm test -- src/lib/bet-ledger.test.ts
```

Expected: FAIL because `dashboard/src/lib/bet-ledger.ts` does not exist.

- [ ] **Step 3: Implement helper module**

Create `dashboard/src/lib/bet-ledger.ts`:

```typescript
import type { BetLedgerResponse, BetLedgerStatus } from '@/lib/api'

export const betLedgerDefaultQuery = {
  status: 'fresh',
  dateRange: 'next_7_days',
} as const

export type BetLedgerTone = 'success' | 'warning' | 'info' | 'muted'

export function buildBetLedgerDisplaySummary(response: BetLedgerResponse) {
  const summary = response.summary
  return {
    cards: [
      { label: 'Fresh', value: String(summary.fresh_count), tone: 'success' as const },
      { label: 'Tracked', value: String(summary.tracked_count), tone: 'info' as const },
      { label: 'Needs result', value: String(summary.needs_result_count), tone: 'warning' as const },
      { label: 'Resulted', value: String(summary.resulted_count), tone: 'info' as const },
      { label: 'Paper P/L', value: formatUnits(summary.paper_profit_loss), tone: summary.paper_profit_loss >= 0 ? 'success' as const : 'warning' as const },
      { label: 'Win rate', value: formatPercent(summary.win_rate), tone: 'info' as const },
    ],
  }
}

export function betLedgerStateLabel(state: BetLedgerStatus): string {
  if (state === 'needs_result') return 'Needs result'
  if (state === 'resulted') return 'Resulted'
  if (state === 'voided') return 'Voided'
  if (state === 'all') return 'All'
  return 'Fresh'
}

export function betLedgerStateTone(state: BetLedgerStatus): BetLedgerTone {
  if (state === 'fresh') return 'success'
  if (state === 'needs_result') return 'warning'
  if (state === 'voided') return 'muted'
  return 'info'
}

function formatUnits(value: number): string {
  const formatted = Math.abs(value).toFixed(1)
  return `${value >= 0 ? '+' : '-'}${formatted}u`
}

function formatPercent(value: number | null): string {
  if (value === null) return '--'
  return `${(value * 100).toFixed(1)}%`
}
```

- [ ] **Step 4: Run helper tests**

Run:

```bash
cd dashboard
npm test -- src/lib/bet-ledger.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit helper module**

Run:

```bash
git add dashboard/src/lib/bet-ledger.ts dashboard/src/lib/bet-ledger.test.ts
git commit -m "feat: add bet ledger frontend helpers"
```

---

### Task 6: Bet Ledger Dashboard UI

**Files:**
- Create: `dashboard/src/components/dashboard/bet-ledger-panel.tsx`
- Modify: `dashboard/src/App.tsx`
- Test: `dashboard/src/lib/bet-ledger.test.ts`

- [ ] **Step 1: Create panel component**

Create `dashboard/src/components/dashboard/bet-ledger-panel.tsx`:

```tsx
import { CalendarClock, ChevronDown, SlidersHorizontal, Trophy } from 'lucide-react'
import { useMemo, useState } from 'react'
import type { BetLedgerDateRange, BetLedgerResponse, BetLedgerRow, BetLedgerStatus } from '@/lib/api'
import {
  betLedgerStateLabel,
  betLedgerStateTone,
  buildBetLedgerDisplaySummary,
} from '@/lib/bet-ledger'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

const statusOptions: Array<{ label: string; value: BetLedgerStatus }> = [
  { label: 'Fresh', value: 'fresh' },
  { label: 'Needs result', value: 'needs_result' },
  { label: 'Resulted', value: 'resulted' },
  { label: 'Voided', value: 'voided' },
  { label: 'All', value: 'all' },
]

const dateOptions: Array<{ label: string; value: BetLedgerDateRange }> = [
  { label: 'Today', value: 'today' },
  { label: 'Tomorrow', value: 'tomorrow' },
  { label: '7 days', value: 'next_7_days' },
  { label: '30 days', value: 'last_30_days' },
  { label: 'All', value: 'all' },
]

export function BetLedgerPanel({
  dateRange,
  error,
  ledger,
  loading,
  onDateRangeChange,
  onStatusChange,
  status,
}: {
  dateRange: BetLedgerDateRange
  error: boolean
  ledger?: BetLedgerResponse
  loading: boolean
  onDateRangeChange: (dateRange: BetLedgerDateRange) => void
  onStatusChange: (status: BetLedgerStatus) => void
  status: BetLedgerStatus
}) {
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const summary = useMemo(
    () => (ledger ? buildBetLedgerDisplaySummary(ledger) : null),
    [ledger],
  )

  return (
    <Card data-testid="bet-ledger-panel">
      <CardHeader className="gap-3">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Trophy className="h-5 w-5" />
              Bet ledger
            </CardTitle>
            <CardDescription>
              Fresh opportunities, unresolved matches, results, probabilities, and paper P/L.
            </CardDescription>
          </div>
          <div className="flex flex-col gap-2">
            <SegmentedControl
              label="Status"
              options={statusOptions}
              value={status}
              onChange={onStatusChange}
            />
            <SegmentedControl
              label="Kickoff"
              options={dateOptions}
              value={dateRange}
              onChange={onDateRangeChange}
            />
          </div>
        </div>
      </CardHeader>
      <CardContent className="grid gap-4">
        {error ? (
          <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-950">
            Bet ledger API is not reachable.
          </div>
        ) : null}
        {loading ? <LedgerSkeleton /> : null}
        {!loading && summary ? (
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-6">
            {summary.cards.map((card) => (
              <div className="rounded-md border border-slate-200 bg-slate-50 p-3" key={card.label}>
                <div className="text-xs font-medium uppercase text-slate-500">{card.label}</div>
                <div className="mt-1 text-lg font-semibold text-slate-950">{card.value}</div>
              </div>
            ))}
          </div>
        ) : null}
        {!loading && ledger && ledger.rows.length === 0 ? (
          <div className="rounded-md border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-600">
            No ledger rows match the active kickoff and status filters.
          </div>
        ) : null}
        {!loading && ledger && ledger.rows.length > 0 ? (
          <LedgerTable
            expandedId={expandedId}
            onToggleExpanded={(id) => setExpandedId(expandedId === id ? null : id)}
            rows={ledger.rows}
          />
        ) : null}
      </CardContent>
    </Card>
  )
}
```

- [ ] **Step 2: Add table helpers to the component file**

Append to the same file:

```tsx
function SegmentedControl<T extends string>({
  label,
  onChange,
  options,
  value,
}: {
  label: string
  onChange: (value: T) => void
  options: Array<{ label: string; value: T }>
  value: T
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-xs font-medium uppercase text-slate-500">{label}</span>
      <div className="flex flex-wrap gap-1 rounded-md border border-slate-200 bg-slate-50 p-1">
        {options.map((option) => (
          <Button
            className="h-8 px-2 text-xs"
            key={option.value}
            onClick={() => onChange(option.value)}
            type="button"
            variant={value === option.value ? 'default' : 'ghost'}
          >
            {option.label}
          </Button>
        ))}
      </div>
    </div>
  )
}

function LedgerTable({
  expandedId,
  onToggleExpanded,
  rows,
}: {
  expandedId: string | null
  onToggleExpanded: (id: string) => void
  rows: BetLedgerRow[]
}) {
  return (
    <div className="overflow-x-auto rounded-md border border-slate-200">
      <table className="w-full min-w-[980px] text-left text-sm">
        <thead className="bg-slate-50 text-slate-600">
          <tr>
            {['Kickoff', 'Match', 'Pick', 'Model %', 'Implied %', 'Edge', 'Odds', 'State', 'Outcome', 'Paper P/L', ''].map((heading) => (
              <th className="border-b border-slate-200 px-3 py-2 font-medium" key={heading}>
                {heading}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <LedgerRow
              expanded={expandedId === row.id}
              key={row.id}
              onToggle={() => onToggleExpanded(row.id)}
              row={row}
            />
          ))}
        </tbody>
      </table>
    </div>
  )
}

function LedgerRow({
  expanded,
  onToggle,
  row,
}: {
  expanded: boolean
  onToggle: () => void
  row: BetLedgerRow
}) {
  return (
    <>
      <tr className="border-b border-slate-100 last:border-0">
        <td className="px-3 py-3 text-slate-700">{formatDate(row.kickoff_at)}</td>
        <td className="max-w-72 px-3 py-3">
          <div className="truncate font-semibold text-slate-950" title={row.match_label}>
            {row.match_label}
          </div>
          <div className="truncate text-xs text-slate-500" title={row.league}>
            {row.league}
          </div>
        </td>
        <td className="px-3 py-3 text-slate-900">{row.selection} / {row.market}</td>
        <td className="px-3 py-3 text-slate-900">{formatPercent(row.model_probability)}</td>
        <td className="px-3 py-3 text-slate-900">{formatPercent(row.implied_probability)}</td>
        <td className="px-3 py-3 text-slate-900">{formatSignedPercent(row.edge)}</td>
        <td className="px-3 py-3 text-slate-900">{formatDecimal(row.odds)}</td>
        <td className="px-3 py-3">
          <Badge className={stateClass(row.state)} variant="secondary">
            {betLedgerStateLabel(row.state)}
          </Badge>
        </td>
        <td className="px-3 py-3 text-slate-900">{row.outcome ?? '--'}</td>
        <td className="px-3 py-3 text-slate-900">{formatUnits(row.paper_profit_loss)}</td>
        <td className="px-3 py-3 text-right">
          <Button className="h-8 w-8 p-0" onClick={onToggle} title="Show row details" type="button" variant="ghost">
            <ChevronDown className="h-4 w-4" />
          </Button>
        </td>
      </tr>
      {expanded ? (
        <tr className="border-b border-slate-100 bg-slate-50">
          <td className="px-3 py-3 text-sm text-slate-700" colSpan={11}>
            <div className="grid gap-2 md:grid-cols-3">
              <Detail label="Rationale" value={row.rationale ?? '--'} />
              <Detail label="Risk flags" value={row.risk_flags.join(', ')} />
              <Detail label="Snapshot" value={row.source_snapshot_at ? formatDate(row.source_snapshot_at) : '--'} />
              <Detail label="Model" value={`${row.model_name ?? '--'} / ${row.model_version ?? '--'}`} />
              <Detail label="Created" value={formatDate(row.created_at)} />
              <Detail label="CLV" value={formatSignedDecimal(row.clv)} />
            </div>
          </td>
        </tr>
      ) : null}
    </>
  )
}
```

- [ ] **Step 3: Add formatting helpers to the component file**

Append:

```tsx
function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs font-medium uppercase text-slate-500">{label}</div>
      <div className="mt-1 text-sm text-slate-900">{value}</div>
    </div>
  )
}

function LedgerSkeleton() {
  return (
    <div className="grid gap-3">
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-6">
        {Array.from({ length: 6 }, (_, index) => (
          <Skeleton className="h-16" key={index} />
        ))}
      </div>
      <Skeleton className="h-56" />
    </div>
  )
}

function stateClass(state: BetLedgerStatus) {
  const tone = betLedgerStateTone(state)
  if (tone === 'success') return 'border border-emerald-200 bg-emerald-50 text-emerald-900'
  if (tone === 'warning') return 'border border-amber-200 bg-amber-50 text-amber-900'
  if (tone === 'muted') return 'border border-slate-200 bg-slate-100 text-slate-600'
  return 'border border-blue-200 bg-blue-50 text-blue-900'
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function formatPercent(value: number | null) {
  return value === null ? '--' : `${(value * 100).toFixed(1)}%`
}

function formatSignedPercent(value: number | null) {
  return value === null ? '--' : `${value >= 0 ? '+' : ''}${(value * 100).toFixed(1)}pp`
}

function formatDecimal(value: number | null) {
  return value === null ? '--' : value.toFixed(2)
}

function formatSignedDecimal(value: number | null) {
  return value === null ? '--' : `${value >= 0 ? '+' : ''}${value.toFixed(3)}`
}

function formatUnits(value: number | null) {
  return value === null ? '--' : `${value >= 0 ? '+' : ''}${value.toFixed(1)}u`
}
```

- [ ] **Step 4: Integrate panel in `App.tsx`**

In `dashboard/src/App.tsx`, add imports:

```tsx
import { BetLedgerPanel } from '@/components/dashboard/bet-ledger-panel'
import { betLedgerDefaultQuery } from '@/lib/bet-ledger'
```

Extend the API import to include:

```tsx
  fetchBetLedger,
```

Extend the type import to include:

```tsx
  BetLedgerDateRange,
  BetLedgerResponse,
  BetLedgerStatus,
```

In `App`, add state before queries:

```tsx
  const [betLedgerQuery, setBetLedgerQuery] = useState(betLedgerDefaultQuery)
```

Add the query:

```tsx
  const betLedger = useQuery({
    queryKey: ['bet-ledger', betLedgerQuery],
    queryFn: () => fetchBetLedger(betLedgerQuery),
  })
```

Pass props to `DashboardContent`:

```tsx
              betLedger={betLedger.data}
              betLedgerDateRange={betLedgerQuery.dateRange}
              betLedgerError={betLedger.isError}
              betLedgerLoading={betLedger.isLoading}
              betLedgerStatus={betLedgerQuery.status}
              onBetLedgerDateRangeChange={(dateRange) =>
                setBetLedgerQuery((current) => ({ ...current, dateRange }))
              }
              onBetLedgerStatusChange={(status) =>
                setBetLedgerQuery((current) => ({ ...current, status }))
              }
```

Add these props to `DashboardContentProps`:

```tsx
  betLedger?: BetLedgerResponse
  betLedgerDateRange: BetLedgerDateRange
  betLedgerError: boolean
  betLedgerLoading: boolean
  betLedgerStatus: BetLedgerStatus
  onBetLedgerDateRangeChange: (dateRange: BetLedgerDateRange) => void
  onBetLedgerStatusChange: (status: BetLedgerStatus) => void
```

Destructure the props in `DashboardContent`.

Replace `OpenPaperBetsPanel` usage with:

```tsx
            <BetLedgerPanel
              dateRange={betLedgerDateRange}
              error={betLedgerError}
              ledger={betLedger}
              loading={betLedgerLoading}
              onDateRangeChange={onBetLedgerDateRangeChange}
              onStatusChange={onBetLedgerStatusChange}
              status={betLedgerStatus}
            />
```

Keep `OpenPaperBetsPanel` temporarily if other code still references it; remove it only after TypeScript confirms it is unused.

- [ ] **Step 5: Run frontend tests and build**

Run:

```bash
cd dashboard
npm test -- src/lib/bet-ledger.test.ts src/lib/api.test.ts
npm run build
```

Expected: PASS and successful Vite build.

- [ ] **Step 6: Commit dashboard UI**

Run:

```bash
git add dashboard/src/App.tsx dashboard/src/components/dashboard/bet-ledger-panel.tsx dashboard/src/lib/bet-ledger.ts dashboard/src/lib/bet-ledger.test.ts
git commit -m "feat: add bet ledger dashboard panel"
```

---

### Task 7: End-To-End Verification

**Files:**
- Read: `docs/superpowers/specs/2026-05-29-bet-ledger-dashboard-design.md`
- Verify: running API and dashboard

- [ ] **Step 1: Run backend verification**

Run:

```bash
pytest tests/unit/test_bet_ledger_service.py tests/unit/test_dashboard_api.py -v
```

Expected: PASS.

- [ ] **Step 2: Run frontend verification**

Run:

```bash
cd dashboard
npm test
npm run build
```

Expected: PASS.

- [ ] **Step 3: Start local services**

In one terminal:

```bash
uvicorn app.api:api --reload --host 127.0.0.1 --port 8000
```

In another terminal:

```bash
cd dashboard
npm run dev -- --host 127.0.0.1
```

Expected: Vite prints a local URL such as `http://127.0.0.1:5173/`.

- [ ] **Step 4: Browser-check the dashboard**

Open the Vite URL in the in-app browser. Verify:

- Bet Ledger section is visible on first screen or near the top of the dashboard.
- Default filters are Fresh and 7 days.
- Summary cards show Fresh, Tracked, Needs result, Resulted, Paper P/L, and Win rate.
- Table shows Model %, Implied %, Edge, Odds, State, Outcome, and Paper P/L.
- Status filters change the endpoint query and visible rows.
- Row expansion shows rationale, risk flags, source snapshot, model, created time, and CLV.
- No voided or unsafe rows appear as current actionable bets in the default Fresh view.

- [ ] **Step 5: Final quality gate**

Run:

```bash
git status --short
```

Expected: only intentional implementation files are modified. Existing unrelated dirty files from earlier work must not be reverted.

Run:

```bash
git log --oneline -5
```

Expected: recent commits include the bet ledger service, endpoint, API client, helpers, and dashboard panel commits.

---

## Self-Review

- Spec coverage: the plan covers unified row model, kickoff-date filtering, default Fresh plus next 7 days, balanced result focus, voided exclusion, backend tests, frontend tests, and browser verification.
- Placeholder scan: no task uses TBD, TODO, "implement later", or undefined follow-up work.
- Type consistency: backend states are `fresh`, `needs_result`, `resulted`, `voided`; frontend types use the same values plus `all` for filtering.
- Scope check: this is one feature with backend API and one dashboard surface. It is appropriate for a single implementation plan.
