import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Engine, select

from app.config import Settings
from app.db.engine import session_scope
from app.db.models import AIAnalysisRun, ThresholdPolicyRun

MINIMUM_SAMPLE_SIZE = 300
EDGE_TIGHTEN_STEP = 0.03
CONFIDENCE_TIGHTEN_STEP = 0.05
MIN_CONFIDENCE_DEFAULT = 0.5


class ThresholdPolicyService:
    def __init__(self, engine: Engine, settings: Settings) -> None:
        self.engine = engine
        self.settings = settings

    def evaluate_latest(self) -> dict[str, Any]:
        with session_scope(self.engine) as session:
            review = _latest_threshold_review(session)
            if review is None:
                raise ValueError("No recommendation backtest threshold review found")
            existing = _policy_for_source(session, review.id)
            if existing is not None:
                return _policy_payload(existing)

            output = _json_object(review.output_json)
            advice = _threshold_advice(output)
            singles = _singles_metrics(output)
            default_values = _default_policy_values(self.settings)
            state, decision, risk_flags = _state_decision_and_risk_flags(advice)
            policy_values = _candidate_policy_values(
                decision=decision,
                decisions=advice.get("decisions", {}),
                current_values=default_values,
            )
            if state == "advisory":
                policy_values = default_values

            evidence = {
                "sample_size": int(advice.get("sample_size") or singles.get("settled_bets") or 0),
                "minimum_sample_size": int(
                    advice.get("minimum_sample_size") or MINIMUM_SAMPLE_SIZE
                ),
                "threshold_advice": advice,
                "singles": singles,
            }
            now = _utc_now_iso()
            policy = ThresholdPolicyRun(
                state=state,
                decision=decision,
                active=False,
                source_backtest_id=review.id,
                source_backtest_name=review.source_id,
                sample_size=evidence["sample_size"],
                roi=_metric(singles.get("roi")),
                hit_rate=_metric(singles.get("hit_rate")),
                brier_score=_metric(singles.get("brier_score")),
                log_loss=_metric(singles.get("log_loss")),
                max_drawdown_units=_metric(singles.get("max_drawdown_units")),
                policy_values_json=json.dumps(policy_values, sort_keys=True),
                rollback_policy_values_json=json.dumps(default_values, sort_keys=True),
                evidence_json=json.dumps(evidence, sort_keys=True),
                rationale=_rationale(advice, decision),
                risk_flags_json=json.dumps(risk_flags, sort_keys=True),
                created_at=now,
                updated_at=now,
            )
            session.add(policy)
            session.flush()
            return _policy_payload(policy)

    def latest(self) -> dict[str, Any] | None:
        with session_scope(self.engine) as session:
            policy = session.scalar(
                select(ThresholdPolicyRun)
                .order_by(ThresholdPolicyRun.created_at.desc(), ThresholdPolicyRun.id.desc())
                .limit(1)
            )
            return _policy_payload(policy) if policy is not None else None

    def active_policy(self) -> dict[str, Any] | None:
        with session_scope(self.engine) as session:
            policy = _active_policy(session)
            return _policy_payload(policy) if policy is not None else None

    def effective_policy_values(self) -> dict[str, Any]:
        active = self.active_policy()
        if active is None:
            return _default_policy_values(self.settings)
        return active["policy_values"]

    def approve(self, policy_id: int, *, reviewer: str, rationale: str) -> dict[str, Any]:
        with session_scope(self.engine) as session:
            policy = _require_policy(session, policy_id)
            if policy.state != "proposed":
                raise ValueError("Only proposed threshold policies can be approved")
            now = _utc_now_iso()
            policy.state = "approved"
            policy.reviewer = reviewer
            policy.review_rationale = rationale
            policy.reviewed_at = now
            policy.updated_at = now
            session.flush()
            return _policy_payload(policy)

    def apply(self, policy_id: int, *, reviewer: str, rationale: str) -> dict[str, Any]:
        with session_scope(self.engine) as session:
            policy = _require_policy(session, policy_id)
            if policy.state != "approved":
                raise ValueError("Threshold policy must be approved before it can be applied")
            now = _utc_now_iso()
            for active in session.scalars(
                select(ThresholdPolicyRun).where(ThresholdPolicyRun.active.is_(True))
            ):
                active.active = False
                if active.state == "applied":
                    active.state = "rolled_back"
                    active.rolled_back_at = now
                    active.updated_at = now
            policy.state = "applied"
            policy.active = True
            policy.reviewer = reviewer
            policy.review_rationale = rationale
            policy.applied_at = now
            policy.updated_at = now
            session.flush()
            return _policy_payload(policy)

    def rollback(self, policy_id: int, *, reviewer: str, rationale: str) -> dict[str, Any]:
        with session_scope(self.engine) as session:
            policy = _require_policy(session, policy_id)
            if policy.state != "applied":
                raise ValueError("Only applied threshold policies can be rolled back")
            now = _utc_now_iso()
            policy.state = "rolled_back"
            policy.active = False
            policy.reviewer = reviewer
            policy.review_rationale = rationale
            policy.rolled_back_at = now
            policy.updated_at = now
            session.flush()
            return _policy_payload(policy)


def _latest_threshold_review(session) -> AIAnalysisRun | None:
    return session.scalar(
        select(AIAnalysisRun)
        .where(
            AIAnalysisRun.analysis_type == "recommendation_backtest_summary",
            AIAnalysisRun.status == "completed",
        )
        .order_by(AIAnalysisRun.created_at.desc(), AIAnalysisRun.id.desc())
        .limit(1)
    )


def _policy_for_source(session, source_backtest_id: int) -> ThresholdPolicyRun | None:
    return session.scalar(
        select(ThresholdPolicyRun)
        .where(ThresholdPolicyRun.source_backtest_id == source_backtest_id)
        .order_by(ThresholdPolicyRun.id.desc())
        .limit(1)
    )


def _active_policy(session) -> ThresholdPolicyRun | None:
    return session.scalar(
        select(ThresholdPolicyRun)
        .where(ThresholdPolicyRun.active.is_(True), ThresholdPolicyRun.state == "applied")
        .order_by(ThresholdPolicyRun.applied_at.desc(), ThresholdPolicyRun.id.desc())
        .limit(1)
    )


def _require_policy(session, policy_id: int) -> ThresholdPolicyRun:
    policy = session.get(ThresholdPolicyRun, policy_id)
    if policy is None:
        raise ValueError(f"Threshold policy not found: {policy_id}")
    return policy


def _threshold_advice(output: dict[str, Any]) -> dict[str, Any]:
    advice = output.get("threshold_advice")
    return advice if isinstance(advice, dict) else {}


def _singles_metrics(output: dict[str, Any]) -> dict[str, Any]:
    direct = output.get("singles")
    if isinstance(direct, dict):
        return direct
    backtest = output.get("recommendation_backtest")
    if isinstance(backtest, dict) and isinstance(backtest.get("singles"), dict):
        return backtest["singles"]
    return {}


def _state_decision_and_risk_flags(advice: dict[str, Any]) -> tuple[str, str, list[str]]:
    sample_size = int(advice.get("sample_size") or 0)
    minimum_sample = int(advice.get("minimum_sample_size") or MINIMUM_SAMPLE_SIZE)
    source_flags = [
        str(flag)
        for flag in advice.get("risk_flags", [])
        if str(flag) != "no_current_risk_flags"
    ]
    raw_decision = str(advice.get("overall_decision") or "keep")
    risk_flags = list(source_flags)
    if sample_size < minimum_sample:
        if "small_threshold_review_sample" not in risk_flags:
            risk_flags.append("small_threshold_review_sample")
        return "advisory", "fail_closed", risk_flags
    if raw_decision == "loosen":
        if "loosening_requires_manual_review" not in risk_flags:
            risk_flags.append("loosening_requires_manual_review")
        return "advisory", "keep", risk_flags
    if "conflicting_threshold_metrics" in risk_flags:
        return "advisory", "keep", risk_flags
    if raw_decision in {"tighten", "disable"}:
        return "proposed", raw_decision, risk_flags or ["no_current_risk_flags"]
    return "advisory", "keep", risk_flags or ["no_current_risk_flags"]


def _candidate_policy_values(
    *,
    decision: str,
    decisions: dict[str, Any],
    current_values: dict[str, Any],
) -> dict[str, Any]:
    values = dict(current_values)
    if decision == "tighten":
        if _decision_value(decisions, "minimum_edge") == "tighten":
            values["min_edge"] = round(float(values["min_edge"]) + EDGE_TIGHTEN_STEP, 6)
        if _decision_value(decisions, "minimum_expected_value") == "tighten":
            values["min_expected_value"] = round(
                float(values["min_expected_value"]) + EDGE_TIGHTEN_STEP,
                6,
            )
        if _decision_value(decisions, "confidence_floor") == "tighten":
            values["min_confidence"] = round(
                float(values["min_confidence"]) + CONFIDENCE_TIGHTEN_STEP,
                6,
            )
        if _decision_value(decisions, "odds_cap") == "tighten":
            values["max_odds"] = min(float(values["max_odds"]), 3.0)
    if decision == "disable":
        values["recommendations_enabled"] = False
        values["combinations_enabled"] = False
    return values


def _decision_value(decisions: dict[str, Any], key: str) -> str | None:
    item = decisions.get(key)
    if not isinstance(item, dict):
        return None
    value = item.get("decision")
    return str(value) if value is not None else None


def _default_policy_values(settings: Settings) -> dict[str, Any]:
    return {
        "min_edge": settings.min_edge,
        "min_expected_value": 0.0,
        "min_odds": settings.min_odds,
        "max_odds": settings.max_odds,
        "min_confidence": MIN_CONFIDENCE_DEFAULT,
        "recommendations_enabled": True,
        "combinations_enabled": False,
    }


def _rationale(advice: dict[str, Any], decision: str) -> str:
    decisions = advice.get("decisions", {})
    if isinstance(decisions, dict):
        rationales = [
            str(value.get("rationale"))
            for value in decisions.values()
            if isinstance(value, dict) and value.get("rationale")
        ]
        if rationales:
            return " ".join(rationales)
    return f"Threshold policy decision: {decision}."


def _policy_payload(policy: ThresholdPolicyRun) -> dict[str, Any]:
    return {
        "id": policy.id,
        "state": policy.state,
        "decision": policy.decision,
        "active": policy.active,
        "source_backtest_id": policy.source_backtest_id,
        "source_backtest_name": policy.source_backtest_name,
        "sample_size": policy.sample_size,
        "metrics": {
            "roi": policy.roi,
            "hit_rate": policy.hit_rate,
            "brier_score": policy.brier_score,
            "log_loss": policy.log_loss,
            "max_drawdown_units": policy.max_drawdown_units,
        },
        "policy_values": _json_object(policy.policy_values_json),
        "rollback_policy_values": _json_object(policy.rollback_policy_values_json),
        "evidence": _json_object(policy.evidence_json),
        "rationale": policy.rationale,
        "risk_flags": _json_list(policy.risk_flags_json),
        "reviewer": policy.reviewer,
        "review_rationale": policy.review_rationale,
        "reviewed_at": policy.reviewed_at,
        "applied_at": policy.applied_at,
        "rolled_back_at": policy.rolled_back_at,
        "created_at": policy.created_at,
        "updated_at": policy.updated_at,
    }


def _json_object(raw: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _json_list(raw: str) -> list[str]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return [str(item) for item in value] if isinstance(value, list) else []


def _metric(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()
