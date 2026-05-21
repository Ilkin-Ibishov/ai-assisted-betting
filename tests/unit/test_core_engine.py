from app.config import Settings
from app.core.prediction_engine import (
    BaselineHeuristicPredictionEngine,
    EloPredictionEngine,
    PredictionInput,
)
from app.core.value_detector import ValueDetector


def test_prediction_engine_calculates_edge_and_confidence() -> None:
    prediction = BaselineHeuristicPredictionEngine().predict(
        PredictionInput(
            match_id=1,
            market="1X2",
            selection="HOME",
            bookmaker_probability=0.40,
            home_form_points_5=2.0,
            away_form_points_5=1.0,
            home_goals_for_avg_5=2.0,
            away_goals_for_avg_5=1.0,
            home_goals_against_avg_5=1.0,
            away_goals_against_avg_5=1.5,
            home_advantage_flag=1,
        )
    )

    assert prediction.model_name == "baseline_heuristic"
    assert prediction.model_version == "v0"
    assert prediction.model_probability == 0.46
    assert prediction.edge == 0.06
    assert prediction.confidence_score == 0.4


def test_value_detector_bets_only_when_edge_and_odds_are_in_range() -> None:
    settings = Settings(
        database_url="sqlite:///:memory:",
        default_sport="football",
        default_market="1X2",
        default_stake_units=1.0,
        min_edge=0.07,
        min_odds=1.70,
        max_odds=3.50,
        feature_version="v0_baseline",
        model_name="baseline_heuristic",
        model_version="v0",
        elo_initial_rating=1500,
        elo_k_factor=20,
        elo_home_advantage=65,
        log_level="INFO",
        live_collection_enabled=False,
    )
    detector = ValueDetector(settings)

    bet_decision = detector.evaluate(edge=0.08, odds_decimal=2.2)
    low_edge_decision = detector.evaluate(edge=0.06, odds_decimal=2.2)
    low_odds_decision = detector.evaluate(edge=0.08, odds_decimal=1.5)
    high_odds_decision = detector.evaluate(edge=0.08, odds_decimal=4.0)

    assert bet_decision.decision == "BET"
    assert bet_decision.expected_value is not None
    assert low_edge_decision.decision == "SKIP"
    assert low_odds_decision.decision == "SKIP"
    assert high_odds_decision.decision == "SKIP"


def test_elo_prediction_engine_uses_team_strength_signal() -> None:
    home_favored = EloPredictionEngine(home_advantage_points=80).predict(
        PredictionInput(
            match_id=1,
            market="1X2",
            selection="HOME",
            bookmaker_probability=0.40,
            home_form_points_5=2.0,
            away_form_points_5=1.0,
            home_goals_for_avg_5=2.0,
            away_goals_for_avg_5=1.0,
            home_goals_against_avg_5=1.0,
            away_goals_against_avg_5=1.5,
            home_advantage_flag=1,
            home_elo_rating=1600,
            away_elo_rating=1450,
        )
    )
    away_favored = EloPredictionEngine(home_advantage_points=80).predict(
        PredictionInput(
            match_id=1,
            market="1X2",
            selection="AWAY",
            bookmaker_probability=0.30,
            home_form_points_5=1.0,
            away_form_points_5=2.0,
            home_goals_for_avg_5=1.0,
            away_goals_for_avg_5=2.0,
            home_goals_against_avg_5=1.5,
            away_goals_against_avg_5=1.0,
            home_advantage_flag=1,
            home_elo_rating=1450,
            away_elo_rating=1600,
        )
    )

    assert home_favored.model_name == "elo"
    assert home_favored.model_version == "v0"
    assert home_favored.model_probability > home_favored.bookmaker_probability
    assert away_favored.model_probability > away_favored.bookmaker_probability
