from dataclasses import dataclass


@dataclass(frozen=True)
class PredictionInput:
    match_id: int
    market: str
    selection: str
    bookmaker_probability: float
    home_form_points_5: float
    away_form_points_5: float
    home_goals_for_avg_5: float
    away_goals_for_avg_5: float
    home_goals_against_avg_5: float
    away_goals_against_avg_5: float
    home_advantage_flag: int
    home_elo_rating: float | None = None
    away_elo_rating: float | None = None
    enrichment_tier: str = "cold_start"
    home_rest_days: float | None = None
    away_rest_days: float | None = None
    home_goal_difference_trend_5: float = 0.0
    away_goal_difference_trend_5: float = 0.0
    odds_movement_velocity: float = 0.0


@dataclass(frozen=True)
class PredictionOutput:
    match_id: int
    market: str
    selection: str
    model_name: str
    model_version: str
    model_probability: float
    bookmaker_probability: float
    edge: float
    confidence_score: float
    decision: str
    reason: str


class BaselineHeuristicPredictionEngine:
    model_name = "baseline_heuristic"
    model_version = "v0"

    def predict(self, prediction_input: PredictionInput) -> PredictionOutput:
        base = prediction_input.bookmaker_probability
        enriched_adjustment = _enriched_home_adjustment(prediction_input)
        adjustment = _home_adjustment(prediction_input) + enriched_adjustment
        if prediction_input.selection == "AWAY":
            adjustment = -adjustment
        elif prediction_input.selection == "DRAW":
            adjustment = -abs(adjustment) * 0.25

        model_probability = round(_clamp(base + adjustment, 0.05, 0.85), 6)
        edge = round(model_probability - base, 6)
        confidence_score = round(min(abs(edge) / 0.15, 1.0), 6)

        return PredictionOutput(
            match_id=prediction_input.match_id,
            market=prediction_input.market,
            selection=prediction_input.selection,
            model_name=self.model_name,
            model_version=self.model_version,
            model_probability=model_probability,
            bookmaker_probability=base,
            edge=edge,
            confidence_score=confidence_score,
            decision="SKIP",
            reason=(
                "baseline heuristic probability generated with enriched feature signal"
                if enriched_adjustment
                else "baseline heuristic probability generated"
            ),
        )


class EloPredictionEngine:
    model_name = "elo"
    model_version = "v0"

    def __init__(self, *, home_advantage_points: float = 65) -> None:
        self.home_advantage_points = home_advantage_points

    def predict(self, prediction_input: PredictionInput) -> PredictionOutput:
        home_rating = prediction_input.home_elo_rating or 1500
        away_rating = prediction_input.away_elo_rating or 1500
        elo_diff = home_rating + self.home_advantage_points - away_rating
        home_strength = 1 / (1 + 10 ** (-elo_diff / 400))
        away_strength = 1 - home_strength

        if prediction_input.selection == "HOME":
            adjustment = (home_strength - 0.5) * 0.18
        elif prediction_input.selection == "AWAY":
            adjustment = (away_strength - 0.5) * 0.18
        else:
            adjustment = -abs(home_strength - 0.5) * 0.05

        model_probability = round(
            _clamp(prediction_input.bookmaker_probability + adjustment, 0.05, 0.85),
            6,
        )
        edge = round(model_probability - prediction_input.bookmaker_probability, 6)
        confidence_score = round(min(abs(edge) / 0.15, 1.0), 6)

        return PredictionOutput(
            match_id=prediction_input.match_id,
            market=prediction_input.market,
            selection=prediction_input.selection,
            model_name=self.model_name,
            model_version=self.model_version,
            model_probability=model_probability,
            bookmaker_probability=prediction_input.bookmaker_probability,
            edge=edge,
            confidence_score=confidence_score,
            decision="SKIP",
            reason="elo probability generated",
        )


def create_prediction_engine(model_name: str, *, elo_home_advantage: float = 65):
    if model_name == "baseline_heuristic":
        return BaselineHeuristicPredictionEngine()
    if model_name == "elo":
        return EloPredictionEngine(home_advantage_points=elo_home_advantage)
    raise ValueError(f"Unsupported prediction model: {model_name}")


def _home_adjustment(prediction_input: PredictionInput) -> float:
    form_diff = prediction_input.home_form_points_5 - prediction_input.away_form_points_5
    home_goal_diff = (
        prediction_input.home_goals_for_avg_5 - prediction_input.home_goals_against_avg_5
    )
    away_goal_diff = (
        prediction_input.away_goals_for_avg_5 - prediction_input.away_goals_against_avg_5
    )
    goal_diff = home_goal_diff - away_goal_diff
    return (
        0.01 * form_diff
        + 0.02 * goal_diff
        + 0.02 * prediction_input.home_advantage_flag
    )


def _enriched_home_adjustment(prediction_input: PredictionInput) -> float:
    if prediction_input.enrichment_tier == "cold_start":
        return 0.0
    rest_advantage = 0.0
    if (
        prediction_input.home_rest_days is not None
        and prediction_input.away_rest_days is not None
    ):
        rest_advantage = _clamp(
            (prediction_input.home_rest_days - prediction_input.away_rest_days) / 10,
            -0.5,
            0.5,
        )
    trend_advantage = _clamp(
        (
            prediction_input.home_goal_difference_trend_5
            - prediction_input.away_goal_difference_trend_5
        )
        / 3,
        -0.5,
        0.5,
    )
    movement_signal = _clamp(-prediction_input.odds_movement_velocity * 2, -0.5, 0.5)
    tier_weight = 0.5 if prediction_input.enrichment_tier == "partial_enriched" else 1.0
    return round(
        tier_weight * (0.015 * rest_advantage + 0.02 * trend_advantage + 0.01 * movement_signal),
        6,
    )


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))
