from app.config import Settings
from app.core.feature_builder import FeatureBuilder
from app.core.paper_bet_logger import PaperBetLogger
from app.core.prediction_engine import (
    BaselineHeuristicPredictionEngine,
    EloPredictionEngine,
    PredictionInput,
)
from app.core.value_detector import ValueDetector
from app.db.models import Match, Prediction


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


def test_prediction_engine_leaves_cold_start_prediction_unchanged() -> None:
    baseline_input = PredictionInput(
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
    enriched_but_cold_start = PredictionInput(
        **{
            **baseline_input.__dict__,
            "enrichment_tier": "cold_start",
            "home_rest_days": 8.0,
            "away_rest_days": 2.0,
            "home_goal_difference_trend_5": 1.5,
            "away_goal_difference_trend_5": -1.0,
            "odds_movement_velocity": -0.08,
        }
    )

    baseline = BaselineHeuristicPredictionEngine().predict(baseline_input)
    cold_start = BaselineHeuristicPredictionEngine().predict(enriched_but_cold_start)

    assert cold_start.model_probability == baseline.model_probability
    assert cold_start.edge == baseline.edge


def test_prediction_engine_uses_full_enriched_strength_signal() -> None:
    cold_start = BaselineHeuristicPredictionEngine().predict(
        PredictionInput(
            match_id=1,
            market="1X2",
            selection="HOME",
            bookmaker_probability=0.40,
            home_form_points_5=1.0,
            away_form_points_5=1.0,
            home_goals_for_avg_5=1.0,
            away_goals_for_avg_5=1.0,
            home_goals_against_avg_5=1.0,
            away_goals_against_avg_5=1.0,
            home_advantage_flag=1,
            enrichment_tier="cold_start",
        )
    )
    enriched = BaselineHeuristicPredictionEngine().predict(
        PredictionInput(
            match_id=1,
            market="1X2",
            selection="HOME",
            bookmaker_probability=0.40,
            home_form_points_5=1.0,
            away_form_points_5=1.0,
            home_goals_for_avg_5=1.0,
            away_goals_for_avg_5=1.0,
            home_goals_against_avg_5=1.0,
            away_goals_against_avg_5=1.0,
            home_advantage_flag=1,
            enrichment_tier="full_enriched",
            home_rest_days=7.0,
            away_rest_days=2.0,
            home_goal_difference_trend_5=1.0,
            away_goal_difference_trend_5=-1.0,
            odds_movement_velocity=-0.08,
        )
    )

    assert enriched.model_probability > cold_start.model_probability
    assert "enriched feature signal" in enriched.reason


def test_feature_builder_marks_cold_start_provenance_when_history_is_missing() -> None:
    match = _match("target", "Alpha", "Beta", "2026-06-10T20:00:00+04:00")
    features = FeatureBuilder(allow_cold_start_features=True).build_for_match(
        match=match,
        completed_matches=[],
        odds_snapshots=[
            _odds(match.id, "HOME", 2.0, "2026-06-10T12:00:00+04:00"),
            _odds(match.id, "DRAW", 3.2, "2026-06-10T12:00:00+04:00"),
            _odds(match.id, "AWAY", 3.8, "2026-06-10T12:00:00+04:00"),
        ],
    )

    home = next(feature for feature in features if feature.selection == "HOME")

    assert home.enrichment_tier == "cold_start"
    assert home.feature_provenance == ("market_overround_normalized", "cold_start_history")
    assert home.home_rest_days is None
    assert home.away_rest_days is None
    assert home.home_goal_difference_trend_5 == 0.0
    assert home.away_goal_difference_trend_5 == 0.0
    assert home.odds_movement_velocity == 0.0


def test_feature_builder_marks_full_enrichment_from_history_and_odds_velocity() -> None:
    match = _match("target", "Alpha", "Beta", "2026-06-10T20:00:00+04:00")
    completed = [
        _completed("alpha-1", "Alpha", "Gamma", "2026-06-08T20:00:00+04:00", 2, 0),
        _completed("alpha-2", "Delta", "Alpha", "2026-06-04T20:00:00+04:00", 1, 2),
        _completed("alpha-3", "Alpha", "Echo", "2026-06-01T20:00:00+04:00", 1, 1),
        _completed("beta-1", "Beta", "Gamma", "2026-06-07T20:00:00+04:00", 0, 1),
        _completed("beta-2", "Delta", "Beta", "2026-06-03T20:00:00+04:00", 2, 0),
        _completed("beta-3", "Beta", "Echo", "2026-05-31T20:00:00+04:00", 1, 1),
    ]
    features = FeatureBuilder(allow_cold_start_features=True).build_for_match(
        match=match,
        completed_matches=completed,
        odds_snapshots=[
            _odds(match.id, "HOME", 2.2, "2026-06-10T10:00:00+04:00"),
            _odds(match.id, "HOME", 2.0, "2026-06-10T12:00:00+04:00"),
            _odds(match.id, "DRAW", 3.2, "2026-06-10T12:00:00+04:00"),
            _odds(match.id, "AWAY", 3.8, "2026-06-10T12:00:00+04:00"),
        ],
    )

    home = next(feature for feature in features if feature.selection == "HOME")

    assert home.enrichment_tier == "full_enriched"
    assert home.feature_provenance == (
        "market_overround_normalized",
        "recent_form",
        "home_away_split",
        "rest_days",
        "goal_difference_trend",
        "odds_movement_velocity",
        "elo_rating",
    )
    assert home.home_rest_days == 2.0
    assert home.away_rest_days == 3.0
    assert home.home_goal_difference_trend_5 == 1.0
    assert home.away_goal_difference_trend_5 == -1.0
    assert home.odds_movement_velocity < 0


def test_feature_builder_marks_external_football_data_csv_provenance() -> None:
    match = _match("target", "Alpha", "Beta", "2026-06-10T20:00:00+04:00")
    completed = [
        _completed("fd-alpha-1", "Alpha", "Gamma", "2026-06-08T20:00:00+04:00", 2, 0),
        _completed("fd-alpha-2", "Delta", "Alpha", "2026-06-04T20:00:00+04:00", 1, 2),
        _completed("fd-alpha-3", "Alpha", "Echo", "2026-06-01T20:00:00+04:00", 1, 1),
        _completed("fd-beta-1", "Beta", "Gamma", "2026-06-07T20:00:00+04:00", 0, 1),
        _completed("fd-beta-2", "Delta", "Beta", "2026-06-03T20:00:00+04:00", 2, 0),
        _completed("fd-beta-3", "Beta", "Echo", "2026-05-31T20:00:00+04:00", 1, 1),
    ]
    for historical_match in completed:
        historical_match.source = "football_data"
    features = FeatureBuilder(allow_cold_start_features=True).build_for_match(
        match=match,
        completed_matches=completed,
        odds_snapshots=[
            _odds(match.id, "HOME", 2.0, "2026-06-10T12:00:00+04:00"),
            _odds(match.id, "DRAW", 3.2, "2026-06-10T12:00:00+04:00"),
            _odds(match.id, "AWAY", 3.8, "2026-06-10T12:00:00+04:00"),
        ],
    )

    home = next(feature for feature in features if feature.selection == "HOME")

    assert home.enrichment_tier == "full_enriched"
    assert "external_context:football_data_csv" in home.feature_provenance


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

    bet_decision = detector.evaluate(edge=0.08, odds_decimal=2.2, model_probability=0.55)
    negative_ev_decision = detector.evaluate(
        edge=0.08,
        odds_decimal=2.2,
        model_probability=0.40,
    )
    low_edge_decision = detector.evaluate(edge=0.06, odds_decimal=2.2)
    low_odds_decision = detector.evaluate(edge=0.08, odds_decimal=1.5)
    high_odds_decision = detector.evaluate(edge=0.08, odds_decimal=4.0)

    assert bet_decision.decision == "BET"
    assert bet_decision.expected_value is not None
    assert negative_ev_decision.decision == "SKIP"
    assert negative_ev_decision.reason == "expected value not positive"
    assert low_edge_decision.decision == "SKIP"
    assert low_odds_decision.decision == "SKIP"
    assert high_odds_decision.decision == "SKIP"


def test_paper_bet_logger_rejects_low_confidence_predictions() -> None:
    prediction = Prediction(
        match_id=1,
        market="1X2",
        selection="HOME",
        model_name="baseline_heuristic",
        model_version="v0",
        model_probability=0.6,
        bookmaker_probability=0.5,
        edge=0.1,
        confidence_score=0.49,
        decision="BET",
    )
    match = Match(
        source="sample",
        source_match_id="match-001",
        league="Sample Premier",
        home_team="Home",
        away_team="Away",
        kickoff_time="2026-06-02T20:00:00+04:00",
        status="scheduled",
    )

    assert (
        PaperBetLogger().should_create(
            prediction=prediction,
            match=match,
            existing_bet=None,
        )
        is False
    )


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


def _match(
    source_match_id: str,
    home_team: str,
    away_team: str,
    kickoff_time: str,
) -> Match:
    return Match(
        id=abs(hash(source_match_id)) % 100000,
        source="sample",
        source_match_id=source_match_id,
        league="Sample Premier",
        home_team=home_team,
        away_team=away_team,
        kickoff_time=kickoff_time,
        status="scheduled",
    )


def _completed(
    source_match_id: str,
    home_team: str,
    away_team: str,
    kickoff_time: str,
    home_score: int,
    away_score: int,
) -> Match:
    match = _match(source_match_id, home_team, away_team, kickoff_time)
    match.status = "completed"
    match.home_score = home_score
    match.away_score = away_score
    match.result = (
        "HOME" if home_score > away_score else "AWAY" if away_score > home_score else "DRAW"
    )
    return match


def _odds(match_id: int, selection: str, odds_decimal: float, snapshot_time: str):
    from app.db.models import OddsSnapshot

    return OddsSnapshot(
        match_id=match_id,
        source="sample",
        bookmaker="Misli.az",
        market="1X2",
        selection=selection,
        odds_decimal=odds_decimal,
        implied_probability=1 / odds_decimal,
        snapshot_time=snapshot_time,
    )
