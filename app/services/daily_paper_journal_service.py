import json
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import Engine, select

from app.db.engine import session_scope
from app.db.models import (
    AIAnalysisRun,
    Match,
    PaperBet,
    PaperJournalEntry,
    PaperRecommendation,
    Prediction,
    ThresholdPolicyRun,
)


class DailyPaperJournalService:
    def __init__(self, engine: Engine, *, product_timezone: str = "Asia/Baku") -> None:
        self.engine = engine
        self.product_timezone = product_timezone

    def generate(
        self,
        *,
        journal_date: str | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        date_value = journal_date or _default_journal_date(
            product_timezone=self.product_timezone,
            now=now,
        )
        with session_scope(self.engine) as session:
            previous = _previous_journal(session, date_value)
            recommendations = _recommendations(session)
            ai_review = _latest_ai_review(session)
            threshold_review = _latest_threshold_review(session)
            threshold_policy = _latest_threshold_policy(session)
            settled = _settled_since_previous_journal(
                session,
                previous.created_at if previous is not None else None,
            )
            open_bets = _open_bets(session)
            summary = _summary(
                recommendations=recommendations,
                ai_review=ai_review,
                settled=settled,
                open_bets=open_bets,
            )
            source_ids = _source_ids(recommendations, ai_review, settled)
            source_ids = _journal_source_ids(source_ids, threshold_review, threshold_policy)
            decision_state = _decision_state(summary)
            payload = {
                "journal_date": date_value,
                "decision_state": decision_state,
                "summary": summary,
                "quality_snapshot": _quality_snapshot(summary),
                "ai_review": _ai_review_payload(ai_review),
                "threshold_review": _threshold_review_payload(threshold_review),
                "threshold_policy": _threshold_policy_payload(threshold_policy),
                "settled_since_previous_journal": settled,
                "open_paper_bets": [_paper_bet_row(item) for item in open_bets],
                "source_ids": source_ids,
            }
            existing = session.scalar(
                select(PaperJournalEntry).where(PaperJournalEntry.journal_date == date_value)
            )
            now = datetime.now(UTC).isoformat()
            if existing is None:
                existing = PaperJournalEntry(
                    journal_date=date_value,
                    decision_state=decision_state,
                    summary_json=json.dumps(payload, sort_keys=True),
                    source_ids_json=json.dumps(source_ids, sort_keys=True),
                    created_at=now,
                    updated_at=now,
                )
                session.add(existing)
            else:
                existing.decision_state = decision_state
                existing.summary_json = json.dumps(payload, sort_keys=True)
                existing.source_ids_json = json.dumps(source_ids, sort_keys=True)
                existing.updated_at = now
            session.flush()
            payload["id"] = existing.id
            payload["created_at"] = existing.created_at
            payload["updated_at"] = existing.updated_at
            return payload

    def latest(self) -> dict[str, Any] | None:
        with session_scope(self.engine) as session:
            entry = session.scalar(
                select(PaperJournalEntry)
                .order_by(PaperJournalEntry.journal_date.desc(), PaperJournalEntry.id.desc())
                .limit(1)
            )
            if entry is None:
                return None
            return _entry_payload(entry)


def _default_journal_date(*, product_timezone: str, now: datetime | None = None) -> str:
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return current.astimezone(ZoneInfo(product_timezone)).date().isoformat()


def _entry_payload(entry: PaperJournalEntry) -> dict[str, Any]:
    payload = json.loads(entry.summary_json)
    payload.setdefault("threshold_review", _threshold_review_payload(None))
    payload.setdefault("threshold_policy", _threshold_policy_payload(None))
    payload["id"] = entry.id
    payload["created_at"] = entry.created_at
    payload["updated_at"] = entry.updated_at
    return payload


def _previous_journal(session, journal_date: str) -> PaperJournalEntry | None:
    return session.scalar(
        select(PaperJournalEntry)
        .where(PaperJournalEntry.journal_date < journal_date)
        .order_by(PaperJournalEntry.journal_date.desc(), PaperJournalEntry.id.desc())
        .limit(1)
    )


def _recommendations(session) -> list[PaperRecommendation]:
    return list(
        session.scalars(
            select(PaperRecommendation)
            .order_by(
                PaperRecommendation.latest_snapshot_time.desc(),
                PaperRecommendation.created_at.desc(),
                PaperRecommendation.id.desc(),
            )
            .limit(500)
        )
    )


def _latest_ai_review(session) -> AIAnalysisRun | None:
    return session.scalar(
        select(AIAnalysisRun)
        .where(AIAnalysisRun.analysis_type == "recommendation_review")
        .order_by(AIAnalysisRun.created_at.desc(), AIAnalysisRun.id.desc())
        .limit(1)
    )


def _latest_threshold_review(session) -> AIAnalysisRun | None:
    return session.scalar(
        select(AIAnalysisRun)
        .where(AIAnalysisRun.analysis_type == "recommendation_backtest_summary")
        .order_by(AIAnalysisRun.created_at.desc(), AIAnalysisRun.id.desc())
        .limit(1)
    )


def _latest_threshold_policy(session) -> ThresholdPolicyRun | None:
    return session.scalar(
        select(ThresholdPolicyRun)
        .order_by(ThresholdPolicyRun.created_at.desc(), ThresholdPolicyRun.id.desc())
        .limit(1)
    )


def _settled_since_previous_journal(
    session,
    previous_created_at: str | None,
) -> list[dict[str, Any]]:
    query = (
        select(PaperBet, Prediction, Match)
        .join(Prediction, PaperBet.prediction_id == Prediction.id)
        .join(Match, PaperBet.match_id == Match.id)
        .where(PaperBet.status.in_(["won", "lost", "void"]))
        .order_by(PaperBet.settled_at.desc(), PaperBet.id.desc())
    )
    if previous_created_at is not None:
        query = query.where(PaperBet.settled_at > previous_created_at)
    return [
        _settled_row(paper_bet, prediction, match)
        for paper_bet, prediction, match in session.execute(query)
    ]


def _open_bets(session) -> list[PaperBet]:
    return list(
        session.scalars(
            select(PaperBet)
            .where(PaperBet.status == "open")
            .order_by(PaperBet.created_at.desc(), PaperBet.id.desc())
            .limit(100)
        )
    )


def _summary(
    *,
    recommendations: list[PaperRecommendation],
    ai_review: AIAnalysisRun | None,
    settled: list[dict[str, Any]],
    open_bets: list[PaperBet],
) -> dict[str, Any]:
    candidates = [item for item in recommendations if _is_actionable(item)]
    watchlist = [item for item in recommendations if _is_watchlist(item)]
    blocked = [item for item in recommendations if not _is_actionable(item)]
    ai_payload = _ai_review_payload(ai_review)
    calibration_adjusted = [
        item for item in recommendations if item.confidence_adjustment_reason is not None
    ]
    return {
        "candidate_count": len(candidates),
        "watchlist_count": len(watchlist),
        "blocked_count": len(blocked),
        "open_paper_bet_count": len(open_bets),
        "settled_count": len(settled),
        "ai_approval_state": ai_payload["approval_state"],
        "ai_summary": ai_payload["short_summary"],
        "top_candidates": [_recommendation_row(item) for item in candidates[:5]],
        "blocked_examples": [_recommendation_row(item) for item in blocked[:5]],
        "calibration_observations": {
            "confidence_adjusted_count": len(calibration_adjusted),
            "adjustment_reasons": sorted(
                {str(item.confidence_adjustment_reason) for item in calibration_adjusted}
            ),
        },
    }


def _quality_snapshot(summary: dict[str, Any]) -> dict[str, Any]:
    if summary["candidate_count"] > 0:
        overall_state = (
            "actionable_present_ai_rejected"
            if summary["ai_approval_state"] == "reject"
            else "actionable_present"
        )
    elif summary["watchlist_count"] > 0:
        overall_state = "watchlist_only"
    elif summary["blocked_count"] > 0:
        overall_state = "all_blocked"
    else:
        overall_state = "empty"
    return {
        "overall_state": overall_state,
        "actionable_count": summary["candidate_count"],
        "watchlist_count": summary["watchlist_count"],
        "blocked_count": summary["blocked_count"],
    }


def _decision_state(summary: dict[str, Any]) -> str:
    if summary["settled_count"] > 0:
        return "settled_learning"
    if summary["candidate_count"] == 0:
        return "no_candidates"
    if summary["ai_approval_state"] == "reject":
        return "ai_rejected"
    return "candidate_ready"


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
    return [str(value) for value in values] if isinstance(values, list) else ["invalid_risk_flags"]


def _json_object(raw: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _json_list(raw: str) -> list[Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return value if isinstance(value, list) else []


def _ai_review_payload(review: AIAnalysisRun | None) -> dict[str, Any]:
    if review is None:
        return {
            "id": None,
            "approval_state": "missing",
            "risk_flags": ["recommendation_review_missing"],
            "short_summary": "No AI recommendation review yet.",
            "concerns": [],
            "recommended_next_actions": [],
        }
    try:
        output = json.loads(review.output_json)
    except json.JSONDecodeError:
        output = {}
    return {
        "id": review.id,
        "approval_state": output.get("approval_state", "missing"),
        "risk_flags": output.get("risk_flags", []),
        "short_summary": output.get("short_summary", "Recommendation review available."),
        "concerns": output.get("concerns", []),
        "recommended_next_actions": output.get("recommended_next_actions", []),
        "created_at": review.created_at,
    }


def _threshold_review_payload(review: AIAnalysisRun | None) -> dict[str, Any]:
    if review is None:
        return {
            "id": None,
            "overall_decision": "missing",
            "risk_flags": ["threshold_review_missing"],
            "decisions": {},
            "short_summary": "No threshold review has been generated yet.",
        }
    try:
        output = json.loads(review.output_json)
    except json.JSONDecodeError:
        output = {}
    advice = output.get("threshold_advice") or {}
    return {
        "id": review.id,
        "overall_decision": advice.get("overall_decision", "missing"),
        "risk_flags": advice.get("risk_flags", []),
        "decisions": advice.get("decisions", {}),
        "short_summary": output.get("short_summary", "Threshold review available."),
        "created_at": review.created_at,
    }


def _source_ids(
    recommendations: list[PaperRecommendation],
    ai_review: AIAnalysisRun | None,
    settled: list[dict[str, Any]],
) -> list[str]:
    ids = [f"paper_recommendation:{item.id}" for item in recommendations[:50]]
    if ai_review is not None:
        ids.append(f"ai_analysis:{ai_review.id}")
    ids.extend([f"paper_bet:{item['paper_bet_id']}" for item in settled[:50]])
    return ids


def _journal_source_ids(
    source_ids: list[str],
    threshold_review: AIAnalysisRun | None,
    threshold_policy: ThresholdPolicyRun | None,
) -> list[str]:
    ids = list(source_ids)
    if threshold_review is None:
        pass
    else:
        ids.append(f"ai_analysis:{threshold_review.id}")
    if threshold_policy is not None:
        ids.append(f"threshold_policy:{threshold_policy.id}")
    return ids


def _threshold_policy_payload(policy: ThresholdPolicyRun | None) -> dict[str, Any]:
    if policy is None:
        return {
            "id": None,
            "state": "missing",
            "decision": "missing",
            "active": False,
            "risk_flags": ["threshold_policy_missing"],
            "policy_values": {},
            "short_summary": "No threshold policy has been evaluated yet.",
        }
    return {
        "id": policy.id,
        "state": policy.state,
        "decision": policy.decision,
        "active": policy.active,
        "sample_size": policy.sample_size,
        "risk_flags": _json_list(policy.risk_flags_json),
        "policy_values": _json_object(policy.policy_values_json),
        "rollback_policy_values": _json_object(policy.rollback_policy_values_json),
        "rationale": policy.rationale,
        "created_at": policy.created_at,
        "updated_at": policy.updated_at,
    }


def _recommendation_row(item: PaperRecommendation) -> dict[str, Any]:
    return {
        "id": item.id,
        "source_match_id": item.source_match_id,
        "selection": item.selection,
        "grade": item.grade,
        "status": item.status,
        "expected_value": item.expected_value,
        "edge": item.edge,
        "confidence_score": item.confidence_score,
        "risk_flags": _risk_flags(item),
        "rationale": item.rationale,
    }


def _settled_row(paper_bet: PaperBet, prediction: Prediction, match: Match) -> dict[str, Any]:
    return {
        "paper_bet_id": paper_bet.id,
        "prediction_id": prediction.id,
        "match_id": match.id,
        "source_match_id": match.source_match_id,
        "selection": paper_bet.selection,
        "status": paper_bet.status,
        "profit_loss_units": paper_bet.profit_loss_units,
        "settled_at": paper_bet.settled_at,
    }


def _paper_bet_row(item: PaperBet) -> dict[str, Any]:
    return {
        "paper_bet_id": item.id,
        "prediction_id": item.prediction_id,
        "match_id": item.match_id,
        "selection": item.selection,
        "status": item.status,
        "expected_value": item.expected_value,
        "created_at": item.created_at,
    }
