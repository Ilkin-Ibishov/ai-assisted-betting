import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from app.db.engine import create_engine_from_url, session_scope
from app.db.models import AIAnalysisRun, LiveRun, PaperCombination, PaperRecommendation
from app.services.worker_monitoring_service import WorkerMonitoringService


class RecommendationQualityService:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def report(
        self,
        *,
        now_iso: str | None = None,
        fresh_after_minutes: int = 90,
        limit: int = 500,
    ) -> dict[str, Any]:
        worker_status = WorkerMonitoringService(self.database_url).status(
            fresh_after_minutes=fresh_after_minutes,
            now_iso=now_iso,
        )
        engine = create_engine_from_url(self.database_url)
        try:
            with session_scope(engine) as session:
                latest_worker = _latest_worker(session)
                recommendations = _latest_recommendations(session, limit=limit)
                combinations = _latest_combinations(session, limit=limit)
                latest_review = _latest_ai_review(session)
        finally:
            engine.dispose()

        latest_worker_started = latest_worker.started_at if latest_worker is not None else None
        fresh_cutoff = (
            _iso_minus_minutes(latest_worker_started, fresh_after_minutes)
            if latest_worker_started is not None
            else None
        )
        actionable = [item for item in recommendations if _is_actionable(item)]
        watchlist = [item for item in recommendations if _is_watchlist(item)]
        rejected = [
            item
            for item in recommendations
            if item.grade == "reject" or item.status != "active"
        ]
        created_since_worker = [
            item
            for item in recommendations
            if latest_worker_started is not None and item.created_at >= latest_worker_started
        ]
        fresh_snapshot_rows = [
            item
            for item in recommendations
            if fresh_cutoff is None or item.latest_snapshot_time >= fresh_cutoff
        ]
        risk_flags = _risk_flag_counter(recommendations)
        positive_blocked = [
            item
            for item in recommendations
            if (item.expected_value or 0) > 0 and not _is_actionable(item)
        ]

        return {
            "overall_state": _overall_state(
                actionable_count=len(actionable),
                watchlist_count=len(watchlist),
                total_count=len(recommendations),
                ai_approval_state=_ai_approval_state(latest_review),
            ),
            "worker": {
                "status": worker_status["status"],
                "healthy": worker_status["healthy"],
                "freshness_minutes": worker_status["freshness_minutes"],
                "fresh_after_minutes": worker_status["fresh_after_minutes"],
                "latest_run_id": latest_worker.id if latest_worker is not None else None,
                "latest_run_started_at": (
                    latest_worker.started_at if latest_worker is not None else None
                ),
                "latest_run_finished_at": (
                    latest_worker.finished_at if latest_worker is not None else None
                ),
            },
            "summary": {
                "total_recommendations": len(recommendations),
                "actionable_count": len(actionable),
                "watchlist_count": len(watchlist),
                "rejected_count": len(rejected),
                "created_since_latest_worker": len(created_since_worker),
                "fresh_snapshot_count": len(fresh_snapshot_rows),
                "latest_snapshot_time": _max_string(
                    [item.latest_snapshot_time for item in recommendations]
                ),
            },
            "distributions": {
                "expected_value": _value_distribution(
                    [item.expected_value for item in recommendations]
                ),
                "edge": _value_distribution([item.edge for item in recommendations]),
                "confidence": _confidence_distribution(
                    [item.confidence_score for item in recommendations]
                ),
                "odds": _odds_distribution([item.current_odds for item in recommendations]),
            },
            "risk_flags": dict(risk_flags),
            "top_actionable": [_recommendation_row(item) for item in _sort_by_ev(actionable)[:5]],
            "top_blocked_positive_ev": [
                _recommendation_row(item) for item in _sort_by_ev(positive_blocked)[:5]
            ],
            "combinations": _combination_summary(combinations),
            "ai_review": _ai_review_summary(latest_review),
        }


def _latest_worker(session) -> LiveRun | None:
    return session.scalar(
        select(LiveRun)
        .where(LiveRun.run_type == "scheduled_paper_worker")
        .order_by(LiveRun.started_at.desc(), LiveRun.id.desc())
        .limit(1)
    )


def _latest_recommendations(session, *, limit: int) -> list[PaperRecommendation]:
    return list(
        session.scalars(
            select(PaperRecommendation)
            .order_by(
                PaperRecommendation.latest_snapshot_time.desc(),
                PaperRecommendation.created_at.desc(),
                PaperRecommendation.id.desc(),
            )
            .limit(max(1, min(limit, 1000)))
        )
    )


def _latest_combinations(session, *, limit: int) -> list[PaperCombination]:
    return list(
        session.scalars(
            select(PaperCombination)
            .order_by(PaperCombination.created_at.desc(), PaperCombination.rank.asc())
            .limit(max(1, min(limit, 1000)))
        )
    )


def _latest_ai_review(session) -> AIAnalysisRun | None:
    return session.scalar(
        select(AIAnalysisRun)
        .where(AIAnalysisRun.analysis_type == "recommendation_review")
        .order_by(AIAnalysisRun.created_at.desc(), AIAnalysisRun.id.desc())
        .limit(1)
    )


def _is_actionable(item: PaperRecommendation) -> bool:
    return (
        item.status == "active"
        and item.grade in {"recommended", "lean"}
        and (item.expected_value or 0) > 0
        and not set(_risk_flags(item)).intersection(_blocking_flags())
    )


def _is_watchlist(item: PaperRecommendation) -> bool:
    return (
        item.status == "active"
        and (item.expected_value or 0) > 0
        and not _is_actionable(item)
        and not set(_risk_flags(item)).intersection(_hard_blocking_flags())
    )


def _blocking_flags() -> set[str]:
    return _hard_blocking_flags() | {"low_confidence"}


def _hard_blocking_flags() -> set[str]:
    return {
        "negative_expected_value",
        "missing_prediction",
        "stale_odds",
        "missing_outcome",
        "provider_health_warning",
        "edge_below_threshold",
    }


def _risk_flags(item: PaperRecommendation) -> list[str]:
    try:
        values = json.loads(item.risk_flags_json)
    except json.JSONDecodeError:
        return ["invalid_risk_flags"]
    if not isinstance(values, list):
        return ["invalid_risk_flags"]
    return [str(value) for value in values]


def _risk_flag_counter(items: list[PaperRecommendation]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for item in items:
        for flag in _risk_flags(item):
            if flag != "no_current_risk_flags":
                counter[flag] += 1
    return counter


def _value_distribution(values: list[float | None]) -> dict[str, int]:
    present = [float(value) for value in values if value is not None]
    return {
        "missing": len(values) - len(present),
        "negative": len([value for value in present if value < 0]),
        "zero": len([value for value in present if value == 0]),
        "positive": len([value for value in present if value > 0]),
        "strong_positive": len([value for value in present if value >= 0.15]),
    }


def _confidence_distribution(values: list[float | None]) -> dict[str, int]:
    present = [float(value) for value in values if value is not None]
    return {
        "missing": len(values) - len(present),
        "low": len([value for value in present if value < 0.5]),
        "medium": len([value for value in present if 0.5 <= value < 0.7]),
        "high": len([value for value in present if value >= 0.7]),
    }


def _odds_distribution(values: list[float | None]) -> dict[str, int]:
    present = [float(value) for value in values if value is not None]
    return {
        "missing": len(values) - len(present),
        "under_1_7": len([value for value in present if value < 1.7]),
        "between_1_7_and_3_5": len([value for value in present if 1.7 <= value <= 3.5]),
        "over_3_5": len([value for value in present if value > 3.5]),
        "over_6": len([value for value in present if value > 6]),
    }


def _sort_by_ev(items: list[PaperRecommendation]) -> list[PaperRecommendation]:
    return sorted(items, key=lambda item: item.expected_value or float("-inf"), reverse=True)


def _recommendation_row(item: PaperRecommendation) -> dict[str, Any]:
    return {
        "id": item.id,
        "source_match_id": item.source_match_id,
        "market": item.market,
        "selection": item.selection,
        "grade": item.grade,
        "status": item.status,
        "current_odds": item.current_odds,
        "expected_value": item.expected_value,
        "edge": item.edge,
        "confidence_score": item.confidence_score,
        "risk_flags": _risk_flags(item),
        "latest_snapshot_time": item.latest_snapshot_time,
        "created_at": item.created_at,
        "rationale": item.rationale,
    }


def _combination_summary(combinations: list[PaperCombination]) -> dict[str, Any]:
    active = [item for item in combinations if item.status == "active"]
    recommended = [item for item in combinations if item.grade == "recommended"]
    return {
        "total": len(combinations),
        "active": len(active),
        "recommended": len(recommended),
        "max_leg_count": max([item.leg_count for item in combinations], default=0),
        "top": [_combination_row(item) for item in combinations[:5]],
    }


def _combination_row(item: PaperCombination) -> dict[str, Any]:
    return {
        "id": item.id,
        "grade": item.grade,
        "status": item.status,
        "rank": item.rank,
        "leg_count": item.leg_count,
        "combined_expected_value": item.combined_expected_value,
        "confidence_score": item.confidence_score,
        "risk_flags": json.loads(item.risk_flags_json),
    }


def _ai_review_summary(review: AIAnalysisRun | None) -> dict[str, Any]:
    if review is None:
        return {
            "id": None,
            "approval_state": "missing",
            "risk_flags": ["recommendation_review_missing"],
            "created_at": None,
            "short_summary": "No AI recommendation review yet.",
        }
    try:
        output = json.loads(review.output_json)
    except json.JSONDecodeError:
        output = {}
    return {
        "id": review.id,
        "approval_state": output.get("approval_state", "missing"),
        "risk_flags": output.get("risk_flags", []),
        "created_at": review.created_at,
        "short_summary": output.get("short_summary", "Recommendation review available."),
        "model_quality": output.get("model_quality"),
    }


def _ai_approval_state(review: AIAnalysisRun | None) -> str:
    return str(_ai_review_summary(review)["approval_state"])


def _overall_state(
    *,
    actionable_count: int,
    watchlist_count: int,
    total_count: int,
    ai_approval_state: str,
) -> str:
    if total_count == 0:
        return "empty"
    if actionable_count > 0:
        if ai_approval_state == "reject":
            return "actionable_present_ai_rejected"
        return "actionable_present"
    if watchlist_count > 0:
        return "watchlist_only"
    return "all_blocked"


def _max_string(values: list[str]) -> str | None:
    return max(values) if values else None


def _iso_minus_minutes(value: str, minutes: int) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return (parsed.astimezone(UTC) - timedelta(minutes=minutes)).isoformat()
