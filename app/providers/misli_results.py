from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class MisliResult:
    source_match_id: str
    misli_event_id: str
    status: str
    home_team: str
    away_team: str
    kickoff_time: str | None
    home_score: int | None
    away_score: int | None
    result: str | None
    raw_payload: dict[str, Any]


FINAL_STATUSES = {"ENDED", "FINISHED", "COMPLETED", "FT"}
SCHEDULED_STATUSES = {"SCHEDULED", "NOT_STARTED", "NS"}
POSTPONED_STATUSES = {"POSTPONED", "DELAYED", "CANCELLED", "CANCELED", "ABANDONED"}


def parse_misli_results_payload(payload: dict[str, Any]) -> list[MisliResult]:
    raw_items = payload.get("data", {}).get("data", [])
    if not isinstance(raw_items, list):
        return []
    results: list[MisliResult] = []
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue
        sg_id = _string_id(raw_item.get("sgId") or raw_item.get("id"))
        if not sg_id:
            continue
        status = _normalize_status(raw_item)
        home_score = _score(raw_item.get("homeTeam"))
        away_score = _score(raw_item.get("awayTeam"))
        final_result = (
            _result_from_score(home_score, away_score)
            if status == "completed" and home_score is not None and away_score is not None
            else None
        )
        results.append(
            MisliResult(
                source_match_id=f"misli:football:{sg_id}",
                misli_event_id=sg_id,
                status=status,
                home_team=_team_name(raw_item.get("homeTeam")),
                away_team=_team_name(raw_item.get("awayTeam")),
                kickoff_time=_kickoff_iso(raw_item.get("date")),
                home_score=home_score,
                away_score=away_score,
                result=final_result,
                raw_payload=raw_item,
            )
        )
    return results


def match_misli_result(match: Any, results: list[MisliResult]) -> MisliResult | None:
    exact = [result for result in results if result.source_match_id == match.source_match_id]
    if len(exact) == 1:
        return exact[0]

    fallback = [
        result
        for result in results
        if _normalize_name(result.home_team) == _normalize_name(match.home_team)
        and _normalize_name(result.away_team) == _normalize_name(match.away_team)
        and _same_kickoff_date(result.kickoff_time, match.kickoff_time)
    ]
    if len(fallback) == 1:
        return fallback[0]
    return None


def _normalize_status(raw_item: dict[str, Any]) -> str:
    status = str(raw_item.get("status") or raw_item.get("live") or "").strip().upper()
    if status in FINAL_STATUSES:
        return "completed"
    if status in SCHEDULED_STATUSES:
        return "scheduled"
    if status in POSTPONED_STATUSES:
        return "postponed"
    if status:
        return "in_progress"
    return "unknown"


def _score(raw_team: Any) -> int | None:
    if not isinstance(raw_team, dict):
        return None
    scores = raw_team.get("scores")
    if not isinstance(scores, dict):
        return None
    for key in ("CURRENT", "FT", "FULL_TIME"):
        value = scores.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip().isdigit():
            return int(value)
    return None


def _team_name(raw_team: Any) -> str:
    if not isinstance(raw_team, dict):
        return ""
    return str(raw_team.get("teamName") or "").strip()


def _kickoff_iso(value: Any) -> str | None:
    if not isinstance(value, int | float):
        return None
    return datetime.fromtimestamp(value / 1000, UTC).isoformat()


def _result_from_score(home_score: int, away_score: int) -> str:
    if home_score > away_score:
        return "HOME"
    if away_score > home_score:
        return "AWAY"
    return "DRAW"


def _normalize_name(value: str) -> str:
    return " ".join(value.casefold().strip().split())


def _same_kickoff_date(left: str | None, right: str | None) -> bool:
    left_date = _date_from_iso(left)
    right_date = _date_from_iso(right)
    return left_date is not None and left_date == right_date


def _date_from_iso(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _string_id(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()
