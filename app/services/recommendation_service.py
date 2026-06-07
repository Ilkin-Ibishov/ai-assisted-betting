import json

from sqlalchemy import Engine, select

from app.config import Settings
from app.db.engine import session_scope
from app.db.models import LiveRun, Prediction
from app.db.repositories import PaperRecommendationRepository
from app.services.odds_movement_service import OddsMovementService
from app.services.prediction_service import StepSummary
from app.services.threshold_policy_service import ThresholdPolicyService

COLD_START_CONFIDENCE_CEILING = 0.15
HIGH_EV_CONFIDENCE_THRESHOLD = 0.15
HIGH_EV_CONFIDENCE_FLOOR = 0.52
MAX_CALIBRATION_ODDS = 6.0


class RecommendationService:
    def __init__(self, engine: Engine, settings: Settings) -> None:
        self.engine = engine
        self.settings = settings

    def generate(self, *, stale_after_minutes: int = 60) -> StepSummary:
        movements = OddsMovementService(self.engine).summaries(
            stale_after_minutes=stale_after_minutes,
            limit=500,
        )
        provider_unhealthy = _provider_unhealthy(self.engine)
        policy_values = ThresholdPolicyService(self.engine, self.settings).effective_policy_values()
        min_edge = float(policy_values.get("min_edge", self.settings.min_edge))
        min_confidence = float(policy_values.get("min_confidence", 0.5))
        min_odds = float(policy_values.get("min_odds", self.settings.min_odds))
        max_odds = float(policy_values.get("max_odds", self.settings.max_odds))
        recommendations_enabled = bool(policy_values.get("recommendations_enabled", True))
        policy_active = (
            ThresholdPolicyService(self.engine, self.settings).active_policy() is not None
        )
        items_read = 0
        items_created = 0
        items_updated = 0
        items_skipped = 0

        with session_scope(self.engine) as session:
            repository = PaperRecommendationRepository(session)
            for movement in movements:
                items_read += 1
                prediction = _latest_prediction(
                    session,
                    match_id=int(movement["match_id"]),
                    market=str(movement["market"]),
                    selection=str(movement["selection"]),
                    model_name=self.settings.model_name,
                    model_version=self.settings.model_version,
                )
                model_probability = prediction.model_probability if prediction else None
                implied_probability = (
                    (1 / float(movement["current_odds"]))
                    if movement.get("current_odds") is not None
                    else None
                )
                edge = prediction.edge if prediction else None
                expected_value = _expected_value(model_probability, movement.get("current_odds"))
                raw_confidence = prediction.confidence_score if prediction else None
                confidence = _calibrated_recommendation_confidence(
                    raw_confidence=raw_confidence,
                    edge=edge,
                    expected_value=expected_value,
                    current_odds=movement.get("current_odds"),
                    min_edge=min_edge,
                )
                confidence_adjustment_reason = _confidence_adjustment_reason(
                    raw_confidence=raw_confidence,
                    recommendation_confidence=confidence,
                )
                grade, risk_flags, rationale = _score_recommendation(
                    movement=movement,
                    edge=edge,
                    confidence=confidence,
                    expected_value=expected_value,
                    min_edge=min_edge,
                    min_confidence=min_confidence,
                    min_odds=min_odds,
                    max_odds=max_odds,
                    recommendations_enabled=recommendations_enabled,
                    policy_active=policy_active,
                    provider_unhealthy=provider_unhealthy,
                    confidence_was_calibrated=(
                        raw_confidence is not None
                        and confidence is not None
                        and confidence > raw_confidence
                    ),
                )
                latest_snapshot_time = str(movement["latest_snapshot_time"])
                recommendation_values = {
                    "match_id": int(movement["match_id"]),
                    "prediction_id": prediction.id if prediction else None,
                    "source_run_id": None,
                    "source_match_id": str(movement["source_match_id"]),
                    "bookmaker": str(movement["bookmaker"]),
                    "market": str(movement["market"]),
                    "selection": str(movement["selection"]),
                    "latest_snapshot_time": latest_snapshot_time,
                    "model_name": self.settings.model_name,
                    "model_version": self.settings.model_version,
                    "grade": grade,
                    "status": "active" if grade != "reject" else "rejected",
                    "model_probability": model_probability,
                    "implied_probability": implied_probability,
                    "edge": edge,
                    "confidence_score": confidence,
                    "model_confidence_score": raw_confidence,
                    "recommendation_confidence_score": confidence,
                    "confidence_adjustment_reason": confidence_adjustment_reason,
                    "current_odds": movement.get("current_odds"),
                    "expected_value": expected_value,
                    "risk_flags_json": json.dumps(risk_flags),
                    "rationale": rationale,
                }
                existing = repository.get_by_identity(
                    source_match_id=str(movement["source_match_id"]),
                    market=str(movement["market"]),
                    selection=str(movement["selection"]),
                    model_name=self.settings.model_name,
                    model_version=self.settings.model_version,
                    latest_snapshot_time=latest_snapshot_time,
                )
                if existing is not None:
                    repository.update(existing, **recommendation_values)
                    items_updated += 1
                    continue

                repository.add(**recommendation_values)
                items_created += 1

        return StepSummary(items_read, items_created, items_updated, items_skipped, 0)


def _latest_prediction(
    session,
    *,
    match_id: int,
    market: str,
    selection: str,
    model_name: str,
    model_version: str,
) -> Prediction | None:
    return session.scalar(
        select(Prediction)
        .where(
            Prediction.match_id == match_id,
            Prediction.market == market,
            Prediction.selection == selection,
            Prediction.model_name == model_name,
            Prediction.model_version == model_version,
        )
        .order_by(Prediction.created_at.desc(), Prediction.id.desc())
        .limit(1)
    )


def _score_recommendation(
    *,
    movement: dict,
    edge: float | None,
    confidence: float | None,
    expected_value: float | None,
    min_edge: float,
    min_confidence: float,
    min_odds: float,
    max_odds: float,
    recommendations_enabled: bool,
    policy_active: bool,
    provider_unhealthy: bool,
    confidence_was_calibrated: bool = False,
) -> tuple[str, list[str], str]:
    risk_flags: list[str] = []
    policy_phrase = " active threshold policy" if policy_active else ""
    movement_status = str(movement.get("status"))
    current_odds = movement.get("current_odds")
    if not recommendations_enabled:
        risk_flags.append("threshold_policy_recommendations_disabled")
    if movement_status == "stale":
        risk_flags.append("stale_odds")
    if movement_status == "missing":
        risk_flags.append("missing_outcome")
    if provider_unhealthy:
        risk_flags.append("provider_health_warning")
    if edge is None:
        risk_flags.append("missing_prediction")
    elif edge < min_edge:
        risk_flags.append("edge_below_threshold")
    if policy_active and current_odds is not None and float(current_odds) < min_odds:
        risk_flags.append("odds_below_policy_minimum")
    if policy_active and current_odds is not None and float(current_odds) > max_odds:
        risk_flags.append("odds_above_policy_cap")
    if expected_value is not None and expected_value <= 0:
        risk_flags.append("negative_expected_value")
    if confidence is not None and confidence < min_confidence:
        risk_flags.append("low_confidence")

    unsafe_live_flags = (
        "threshold_policy_recommendations_disabled",
        "stale_odds",
        "missing_outcome",
        "provider_health_warning",
        "odds_below_policy_minimum",
        "odds_above_policy_cap",
    )
    if any(flag in risk_flags for flag in unsafe_live_flags):
        return (
            "reject",
            risk_flags,
            f"Rejected because live odds/provider state or{policy_phrase} is not healthy enough.",
        )
    if edge is None:
        return "reject", risk_flags, "Rejected because no model prediction is available."
    if edge < min_edge:
        return "reject", risk_flags, f"Rejected because edge is below{policy_phrase} threshold."
    if expected_value is not None and expected_value <= 0:
        return "reject", risk_flags, "Rejected because current-odds EV is not positive."
    if confidence is not None and confidence < min_confidence:
        return "watch", risk_flags, "Positive edge exists, but confidence is low."
    if edge >= min_edge * 1.5:
        if confidence_was_calibrated:
            return (
                "recommended",
                risk_flags or ["no_current_risk_flags"],
                "Positive edge is above recommendation threshold with calibrated "
                "high-EV confidence.",
            )
        return (
            "recommended",
            risk_flags or ["no_current_risk_flags"],
            "Positive edge is above recommendation threshold.",
        )
    if confidence_was_calibrated:
        return (
            "lean",
            risk_flags or ["no_current_risk_flags"],
            "Positive edge is above minimum threshold with calibrated high-EV confidence.",
        )
    return (
        "lean",
        risk_flags or ["no_current_risk_flags"],
        "Positive edge is above minimum threshold.",
    )


def _expected_value(model_probability: float | None, odds_decimal: object) -> float | None:
    if model_probability is None or odds_decimal is None:
        return None
    return (model_probability * float(odds_decimal)) - 1


def _calibrated_recommendation_confidence(
    *,
    raw_confidence: float | None,
    edge: float | None,
    expected_value: float | None,
    current_odds: object,
    min_edge: float,
) -> float | None:
    if raw_confidence is None:
        return None
    if edge is None or expected_value is None or current_odds is None:
        return raw_confidence
    odds = float(current_odds)
    if (
        raw_confidence <= COLD_START_CONFIDENCE_CEILING
        and edge >= min_edge
        and expected_value >= HIGH_EV_CONFIDENCE_THRESHOLD
        and odds <= MAX_CALIBRATION_ODDS
    ):
        ev_lift = min((expected_value - HIGH_EV_CONFIDENCE_THRESHOLD) / 2, 0.13)
        return round(max(raw_confidence, HIGH_EV_CONFIDENCE_FLOOR + ev_lift), 6)
    return raw_confidence


def _confidence_adjustment_reason(
    *,
    raw_confidence: float | None,
    recommendation_confidence: float | None,
) -> str | None:
    if (
        raw_confidence is not None
        and recommendation_confidence is not None
        and recommendation_confidence > raw_confidence
    ):
        return "high_ev_confidence_calibration"
    return None


def _provider_unhealthy(engine: Engine) -> bool:
    with session_scope(engine) as session:
        latest_provider_run = session.scalar(
            select(LiveRun)
            .where(LiveRun.provider == "misli_public")
            .order_by(LiveRun.started_at.desc(), LiveRun.id.desc())
            .limit(1)
        )
        return latest_provider_run is not None and latest_provider_run.status == "failed"
