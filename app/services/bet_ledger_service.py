from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, timezone
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

PROVIDER_TIMEZONE = timezone(timedelta(hours=4))


@dataclass(frozen=True)
class DateWindow:
    start: date | None
    end: date | None


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
        reference_time = now or _default_reference_time()
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
                date_filtered_rows = _build_rows(
                    paper_rows=paper_rows,
                    recommendation_rows=recommendation_rows,
                    window=window,
                    include_voided=include_voided or status in {"all", "voided"},
                    now=reference_time,
                )
                rows = _filter_rows(
                    date_filtered_rows,
                    status=status,
                    limit=max(1, min(limit, 500)),
                )
                return {"summary": _summary(date_filtered_rows), "rows": rows}
        finally:
            engine.dispose()


def _build_rows(
    *,
    paper_rows: list[tuple[PaperBet, Prediction, Match]],
    recommendation_rows: list[tuple[PaperRecommendation, Match]],
    window: DateWindow,
    include_voided: bool,
    now: datetime,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    tracked_keys: set[tuple[int, str, str]] = set()

    for paper_bet, prediction, match in paper_rows:
        tracked_keys.add((paper_bet.match_id, paper_bet.market, paper_bet.selection))
        row = _paper_bet_row(paper_bet, prediction, match, now=now)
        if _row_is_date_eligible(
            row,
            window=window,
            include_voided=include_voided,
            local_tz=now.tzinfo or PROVIDER_TIMEZONE,
        ):
            rows.append(row)

    for recommendation, match in recommendation_rows:
        key = (recommendation.match_id, recommendation.market, recommendation.selection)
        if key in tracked_keys:
            continue
        row = _recommendation_row(recommendation, match, now=now)
        if not row["is_valid_open"]:
            continue
        if _row_is_date_eligible(
            row,
            window=window,
            include_voided=include_voided,
            local_tz=now.tzinfo or PROVIDER_TIMEZONE,
        ):
            rows.append(row)

    rows.sort(key=lambda row: (row["kickoff_at"] or "", row["row_type"], row["id"]))
    return rows


def _filter_rows(
    rows: list[dict[str, Any]],
    *,
    status: LedgerStatus,
    limit: int,
) -> list[dict[str, Any]]:
    return [row for row in rows if _row_matches_status(row, status=status)][:limit]


def _row_is_date_eligible(
    row: dict[str, Any],
    *,
    window: DateWindow,
    include_voided: bool,
    local_tz: timezone,
) -> bool:
    if row["state"] == "voided" and not include_voided:
        return False
    kickoff_day = _parse_iso_date(row["kickoff_at"], local_tz=local_tz)
    if kickoff_day is None:
        return False
    if window.start is not None and kickoff_day < window.start:
        return False
    if window.end is not None and kickoff_day >= window.end:
        return False
    return True


def _row_matches_status(row: dict[str, Any], *, status: LedgerStatus) -> bool:
    if status == "all":
        return True
    if row["state"] != status:
        return False
    if status == "fresh":
        return row["is_valid_open"] is True
    return True


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
        "row_type": "tracked",
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
    row = {
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
        "grade": recommendation.grade,
        "state": state,
        "status": recommendation.status,
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
    row["is_valid_open"] = _recommendation_is_valid_open(row)
    return row


def _paper_bet_state(paper_bet: PaperBet, match: Match, *, now: datetime) -> str:
    if paper_bet.status in {"void", "voided", "cancelled", "canceled"}:
        return "voided"
    if paper_bet.status != "open":
        return "resulted"
    return "fresh" if _is_future(match.kickoff_time, now=now) else "needs_result"


def _recommendation_is_valid_open(row: dict[str, Any]) -> bool:
    return (
        row["state"] == "fresh"
        and row["status"] == "active"
        and row["grade"] == "recommended"
        and row["risk_flags"] == ["no_current_risk_flags"]
    )


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
        "fresh_count": sum(1 for row in rows if row["state"] == "fresh" and row["is_valid_open"]),
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
    today = now.date()
    if date_range == "all":
        return DateWindow(None, None)
    if date_range == "today":
        return _day_window(today)
    if date_range == "tomorrow":
        return _day_window(today + timedelta(days=1))
    if date_range == "next_7_days":
        return DateWindow(today, today + timedelta(days=7))
    if date_range == "last_7_days":
        return DateWindow(today - timedelta(days=6), today + timedelta(days=1))
    if date_range == "last_30_days":
        return DateWindow(today - timedelta(days=29), today + timedelta(days=1))
    if date_range == "custom":
        return DateWindow(_parse_date_start(from_date), _parse_date_end(to_date))
    return DateWindow(today, today + timedelta(days=7))


def _default_reference_time() -> datetime:
    return datetime.now(PROVIDER_TIMEZONE)


def _day_window(day: date) -> DateWindow:
    return DateWindow(day, day + timedelta(days=1))


def _parse_date_start(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _parse_date_end(value: str | None) -> date | None:
    return date.fromisoformat(value) + timedelta(days=1) if value else None


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


def _parse_iso_date(value: str | None, *, local_tz: timezone) -> date | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(local_tz).date()
