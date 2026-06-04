import itertools
import json
import math

from sqlalchemy import Engine, select

from app.db.engine import session_scope
from app.db.models import Match, PaperRecommendation
from app.db.repositories import PaperCombinationRepository
from app.services.prediction_service import StepSummary


class CombinationService:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def generate(
        self,
        *,
        max_legs: int = 3,
        min_leg_confidence: float = 0.6,
        max_risk_flags: int = 6,
        max_combinations: int = 100,
    ) -> StepSummary:
        max_legs = max(1, min(max_legs, 6))
        candidates = _eligible_recommendations(self.engine, min_leg_confidence)
        generated = _generate_combinations(candidates, max_legs=max_legs)
        risk_limited = [
            combination
            for combination in generated
            if _risk_flag_count(combination["risk_flags"]) <= max(0, max_risk_flags)
        ]
        ranked = _rank_combinations(risk_limited)[: max(1, min(max_combinations, 500))]

        items_created = 0
        items_skipped = 0
        with session_scope(self.engine) as session:
            repository = PaperCombinationRepository(session)
            for rank, combination in enumerate(ranked, start=1):
                leg_ids_json = json.dumps([leg.id for leg in combination["legs"]])
                model_name = str(combination["legs"][0].model_name)
                model_version = str(combination["legs"][0].model_version)
                if repository.exists(
                    leg_recommendation_ids_json=leg_ids_json,
                    model_name=model_name,
                    model_version=model_version,
                ):
                    items_skipped += 1
                    continue
                repository.add(
                    leg_recommendation_ids_json=leg_ids_json,
                    leg_count=len(combination["legs"]),
                    model_name=model_name,
                    model_version=model_version,
                    grade=combination["grade"],
                    status="active",
                    rank=rank,
                    combined_odds=combination["combined_odds"],
                    estimated_probability=combination["estimated_probability"],
                    combined_expected_value=combination["combined_expected_value"],
                    confidence_score=combination["confidence_score"],
                    risk_flags_json=json.dumps(combination["risk_flags"]),
                    rationale=combination["rationale"],
                )
                items_created += 1

        return StepSummary(len(candidates), items_created, 0, items_skipped, 0)


def _eligible_recommendations(
    engine: Engine,
    min_leg_confidence: float,
) -> list[PaperRecommendation]:
    with session_scope(engine) as session:
        recommendations = list(
            session.execute(
                select(PaperRecommendation, Match)
                .join(Match, PaperRecommendation.match_id == Match.id)
                .where(
                    PaperRecommendation.status == "active",
                    PaperRecommendation.grade.in_(["recommended", "lean", "watch"]),
                )
                .order_by(PaperRecommendation.expected_value.desc())
            )
        )
        enriched = []
        for recommendation, match in recommendations:
            recommendation._match_league = match.league
            recommendation._match_home_team = match.home_team
            recommendation._match_away_team = match.away_team
            enriched.append(recommendation)
        return [
            recommendation
            for recommendation in enriched
            if _leg_is_eligible(recommendation, min_leg_confidence)
        ]


def _leg_is_eligible(recommendation: PaperRecommendation, min_leg_confidence: float) -> bool:
    risk_flags = set(json.loads(recommendation.risk_flags_json))
    if risk_flags.intersection({"stale_odds", "missing_outcome", "provider_health_warning"}):
        return False
    if recommendation.confidence_score is None:
        return False
    if recommendation.confidence_score < min_leg_confidence:
        return False
    if recommendation.current_odds is None or recommendation.model_probability is None:
        return False
    return True


def _generate_combinations(
    candidates: list[PaperRecommendation],
    *,
    max_legs: int,
) -> list[dict]:
    combinations = []
    for leg_count in range(1, max_legs + 1):
        for legs in itertools.combinations(candidates, leg_count):
            combinations.append(_build_combination(legs))
    return combinations


def _build_combination(legs: tuple[PaperRecommendation, ...]) -> dict:
    combined_odds = math.prod(float(leg.current_odds) for leg in legs)
    estimated_probability = math.prod(float(leg.model_probability) for leg in legs)
    confidence_score = sum(float(leg.confidence_score or 0) for leg in legs) / len(legs)
    combined_expected_value = (estimated_probability * combined_odds) - 1
    risk_flags = _combination_risk_flags(legs, combined_expected_value)
    grade = _combination_grade(combined_expected_value, confidence_score, len(legs), risk_flags)
    return {
        "legs": legs,
        "combined_odds": combined_odds,
        "estimated_probability": estimated_probability,
        "combined_expected_value": combined_expected_value,
        "confidence_score": confidence_score,
        "risk_flags": risk_flags,
        "grade": grade,
        "rationale": _combination_rationale(grade, len(legs), combined_expected_value),
    }


def _combination_risk_flags(
    legs: tuple[PaperRecommendation, ...],
    combined_expected_value: float,
) -> list[str]:
    risk_flags: list[str] = []
    if len(legs) > 1:
        risk_flags.append("experimental_combination")
    if len({leg.source_match_id for leg in legs}) != len(legs):
        risk_flags.append("same_match_exposure")
    teams = [
        team
        for leg in legs
        for team in (
            getattr(leg, "_match_home_team", None),
            getattr(leg, "_match_away_team", None),
        )
        if team
    ]
    if len(set(teams)) != len(teams):
        risk_flags.append("duplicate_team_exposure")
    leagues = [getattr(leg, "_match_league", None) for leg in legs]
    leagues = [league for league in leagues if league]
    if len(legs) > 1 and len(set(leagues)) < len(leagues):
        risk_flags.append("same_league_exposure")
    match_markets = [(leg.source_match_id, leg.market) for leg in legs]
    if len(legs) > 1 and len(set(match_markets)) < len(match_markets):
        risk_flags.append("correlated_market_exposure")
    if len(legs) > 2:
        risk_flags.append("higher_leg_count")
    if combined_expected_value < 0:
        risk_flags.append("negative_combined_ev")
    return risk_flags or ["no_current_risk_flags"]


def _combination_grade(
    combined_expected_value: float,
    confidence_score: float,
    leg_count: int,
    risk_flags: list[str],
) -> str:
    if "negative_combined_ev" in risk_flags or "same_match_exposure" in risk_flags:
        return "reject"
    if leg_count == 1:
        return "single"
    return "research"


def _combination_rationale(grade: str, leg_count: int, expected_value: float) -> str:
    return (
        f"{grade.title()} paper combination with {leg_count} leg(s) and "
        f"combined expected value {expected_value:.3f}."
    )


def _risk_flag_count(risk_flags: list[str]) -> int:
    return len([flag for flag in risk_flags if flag != "no_current_risk_flags"])


def _rank_combinations(combinations: list[dict]) -> list[dict]:
    return sorted(
        combinations,
        key=lambda combination: (
            combination["combined_expected_value"],
            combination["confidence_score"],
            -combination["combined_odds"],
        ),
        reverse=True,
    )
