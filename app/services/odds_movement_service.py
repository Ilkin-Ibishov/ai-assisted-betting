from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Engine, select

from app.db.engine import session_scope
from app.db.models import Match, OddsSnapshot


class OddsMovementService:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def summaries(
        self,
        *,
        now: datetime | None = None,
        stale_after_minutes: int = 60,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        now = now or datetime.now(UTC)
        with session_scope(self.engine) as session:
            rows = list(
                session.execute(
                    select(OddsSnapshot, Match)
                    .join(Match, Match.id == OddsSnapshot.match_id)
                    .order_by(OddsSnapshot.snapshot_time.asc(), OddsSnapshot.id.asc())
                )
            )

        grouped: dict[tuple[int, str, str, str], list[tuple[OddsSnapshot, Match]]] = {}
        market_latest: dict[tuple[int, str, str], str] = {}
        for snapshot, match in rows:
            selection_key = (
                snapshot.match_id,
                snapshot.bookmaker,
                snapshot.market,
                snapshot.selection,
            )
            market_key = (snapshot.match_id, snapshot.bookmaker, snapshot.market)
            grouped.setdefault(selection_key, []).append((snapshot, match))
            market_latest[market_key] = max(
                market_latest.get(market_key, snapshot.snapshot_time),
                snapshot.snapshot_time,
            )

        summaries = []
        for (match_id, bookmaker, market, selection), history in grouped.items():
            latest, match = history[-1]
            market_key = (match_id, bookmaker, market)
            latest_market_time = market_latest[market_key]
            latest_for_selection_time = latest.snapshot_time
            is_missing = latest_for_selection_time < latest_market_time
            is_stale = _is_stale(latest_for_selection_time, now, stale_after_minutes)
            opening = history[0][0]
            previous = history[-2][0] if len(history) > 1 else None
            if is_missing:
                status = "missing"
                movement_direction = "missing"
                current_odds = None
                previous_odds = latest.odds_decimal
            elif is_stale:
                status = "stale"
                movement_direction = "stale"
                current_odds = latest.odds_decimal
                previous_odds = previous.odds_decimal if previous is not None else None
            else:
                status = "active"
                current_odds = latest.odds_decimal
                previous_odds = previous.odds_decimal if previous is not None else None
                movement_direction = _movement_direction(current_odds, previous_odds)

            summaries.append(
                {
                    "match_id": match_id,
                    "source": latest.source,
                    "source_match_id": match.source_match_id,
                    "league": match.league,
                    "home_team": match.home_team,
                    "away_team": match.away_team,
                    "kickoff_time": match.kickoff_time,
                    "bookmaker": bookmaker,
                    "market": market,
                    "selection": selection,
                    "opening_odds": opening.odds_decimal,
                    "previous_odds": previous_odds,
                    "current_odds": current_odds,
                    "latest_snapshot_time": latest_for_selection_time,
                    "market_latest_snapshot_time": latest_market_time,
                    "movement_direction": movement_direction,
                    "status": status,
                    "is_stale": is_stale,
                    "snapshots_count": len(history),
                }
            )

        summaries.sort(
            key=lambda item: (
                str(item["latest_snapshot_time"]),
                str(item["source_match_id"]),
                str(item["market"]),
                str(item["selection"]),
            ),
            reverse=True,
        )
        return summaries[: max(1, min(limit, 500))]


def _movement_direction(current_odds: float, previous_odds: float | None) -> str:
    if previous_odds is None:
        return "new"
    if current_odds > previous_odds:
        return "up"
    if current_odds < previous_odds:
        return "down"
    return "stable"


def _is_stale(snapshot_time: str, now: datetime, stale_after_minutes: int) -> bool:
    parsed = _parse_datetime(snapshot_time)
    if parsed is None:
        return True
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return (now.astimezone(UTC) - parsed.astimezone(UTC)).total_seconds() > (
        stale_after_minutes * 60
    )


def _parse_datetime(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
