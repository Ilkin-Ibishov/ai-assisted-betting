import json

from sqlalchemy import select

from app.config import Settings
from app.db.engine import create_engine_from_url, session_scope
from app.db.models import Base, LiveRun, PaperRecommendation, ThresholdPolicyRun
from app.db.repositories import (
    LiveRunRepository,
    MatchRepository,
    OddsSnapshotRepository,
    PredictionRepository,
)
from app.services.recommendation_service import RecommendationService


def test_recommendation_service_persists_recommended_positive_edge(tmp_path) -> None:
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / 'recs.sqlite').as_posix()}")
    Base.metadata.create_all(engine)
    _seed_candidate(engine, edge=0.12, confidence=0.72)

    summary = RecommendationService(engine, _settings()).generate(stale_after_minutes=100000)

    assert summary.items_read == 1
    assert summary.items_created == 1
    assert summary.errors_count == 0
    with session_scope(engine) as session:
        recommendation = session.scalar(select(PaperRecommendation))

    assert recommendation is not None
    assert recommendation.grade == "recommended"
    assert recommendation.status == "active"
    assert recommendation.edge == 0.12
    assert recommendation.expected_value > 0
    assert json.loads(recommendation.risk_flags_json) == ["no_current_risk_flags"]
    assert "Positive edge" in recommendation.rationale


def test_recommendation_service_rejects_negative_edge_without_silently_omitting(
    tmp_path,
) -> None:
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / 'recs.sqlite').as_posix()}")
    Base.metadata.create_all(engine)
    _seed_candidate(engine, edge=-0.02, confidence=0.8)

    RecommendationService(engine, _settings()).generate(stale_after_minutes=100000)

    with session_scope(engine) as session:
        recommendation = session.scalar(select(PaperRecommendation))

    assert recommendation is not None
    assert recommendation.grade == "reject"
    assert "edge_below_threshold" in json.loads(recommendation.risk_flags_json)
    assert "below threshold" in recommendation.rationale


def test_recommendation_service_rejects_stale_odds(tmp_path) -> None:
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / 'recs.sqlite').as_posix()}")
    Base.metadata.create_all(engine)
    _seed_candidate(engine, edge=0.12, confidence=0.8, snapshot_time="2026-05-19T10:00:00+00:00")

    RecommendationService(engine, _settings()).generate(stale_after_minutes=30)

    with session_scope(engine) as session:
        recommendation = session.scalar(select(PaperRecommendation))

    assert recommendation is not None
    assert recommendation.grade == "reject"
    assert "stale_odds" in json.loads(recommendation.risk_flags_json)


def test_recommendation_service_marks_low_confidence_candidate_as_watch(tmp_path) -> None:
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / 'recs.sqlite').as_posix()}")
    Base.metadata.create_all(engine)
    _seed_candidate(engine, edge=0.12, confidence=0.3)

    RecommendationService(engine, _settings()).generate(stale_after_minutes=100000)

    with session_scope(engine) as session:
        recommendation = session.scalar(select(PaperRecommendation))

    assert recommendation is not None
    assert recommendation.grade == "watch"
    assert "low_confidence" in json.loads(recommendation.risk_flags_json)


def test_recommendation_service_calibrates_cold_start_confidence_for_high_ev_candidate(
    tmp_path,
) -> None:
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / 'recs.sqlite').as_posix()}")
    Base.metadata.create_all(engine)
    _seed_candidate(
        engine,
        edge=0.08,
        confidence=0.133333,
        odds_decimal=4.64,
    )

    RecommendationService(engine, _settings()).generate(stale_after_minutes=100000)

    with session_scope(engine) as session:
        recommendation = session.scalar(select(PaperRecommendation))

    assert recommendation is not None
    assert recommendation.grade == "lean"
    assert recommendation.status == "active"
    assert recommendation.confidence_score is not None
    assert recommendation.confidence_score >= 0.5
    assert "low_confidence" not in json.loads(recommendation.risk_flags_json)
    assert "calibrated" in recommendation.rationale


def test_recommendation_service_preserves_raw_confidence_when_calibrated(
    tmp_path,
) -> None:
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / 'recs.sqlite').as_posix()}")
    Base.metadata.create_all(engine)
    _seed_candidate(
        engine,
        edge=0.08,
        confidence=0.133333,
        odds_decimal=4.64,
    )

    RecommendationService(engine, _settings()).generate(stale_after_minutes=100000)

    with session_scope(engine) as session:
        recommendation = session.scalar(select(PaperRecommendation))

    assert recommendation is not None
    assert recommendation.model_confidence_score == 0.133333
    assert recommendation.recommendation_confidence_score == recommendation.confidence_score
    assert recommendation.recommendation_confidence_score is not None
    assert recommendation.recommendation_confidence_score >= 0.5
    assert recommendation.confidence_adjustment_reason == "high_ev_confidence_calibration"


def test_recommendation_service_rejects_negative_current_odds_ev(tmp_path) -> None:
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / 'recs.sqlite').as_posix()}")
    Base.metadata.create_all(engine)
    _seed_candidate(
        engine,
        edge=0.12,
        confidence=0.8,
        model_probability=0.4,
        prediction_bookmaker_probability=0.28,
    )

    RecommendationService(engine, _settings()).generate(stale_after_minutes=100000)

    with session_scope(engine) as session:
        recommendation = session.scalar(select(PaperRecommendation))

    assert recommendation is not None
    assert round(recommendation.expected_value or 0, 6) == -0.2
    assert recommendation.grade == "reject"
    assert recommendation.status == "rejected"
    assert "negative_expected_value" in json.loads(recommendation.risk_flags_json)


def test_recommendation_service_updates_existing_snapshot_recommendation(tmp_path) -> None:
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / 'recs.sqlite').as_posix()}")
    Base.metadata.create_all(engine)
    _seed_candidate(engine, edge=0.12, confidence=0.8)

    first_summary = RecommendationService(engine, _settings()).generate(stale_after_minutes=100000)
    with session_scope(engine) as session:
        original = session.scalar(select(PaperRecommendation))
        assert original is not None
        original_id = original.id

    _seed_new_prediction(engine, edge=0.12, confidence=0.8, model_probability=0.4)

    second_summary = RecommendationService(engine, _settings()).generate(stale_after_minutes=100000)

    assert first_summary.items_created == 1
    assert second_summary.items_created == 0
    assert second_summary.items_updated == 1
    assert second_summary.items_skipped == 0
    with session_scope(engine) as session:
        recommendations = session.scalars(select(PaperRecommendation)).all()

    assert len(recommendations) == 1
    recommendation = recommendations[0]
    assert recommendation.id == original_id
    assert recommendation.grade == "reject"
    assert recommendation.status == "rejected"
    assert round(recommendation.expected_value or 0, 6) == -0.2
    assert "negative_expected_value" in json.loads(recommendation.risk_flags_json)


def test_recommendation_service_rejects_when_provider_health_is_unhealthy(tmp_path) -> None:
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / 'recs.sqlite').as_posix()}")
    Base.metadata.create_all(engine)
    _seed_candidate(engine, edge=0.12, confidence=0.8)
    with session_scope(engine) as session:
        repository = LiveRunRepository(session)
        repository.start(
            run_id="failed-provider",
            run_type="collect_odds",
            provider="misli_public",
        )
        repository.fail(
            run_id="failed-provider",
            errors_count=1,
            error_summary="Misli snapshot contains no events; possible Misli parser drift",
        )

    RecommendationService(engine, _settings()).generate(stale_after_minutes=100000)

    with session_scope(engine) as session:
        recommendation = session.scalar(select(PaperRecommendation))
        provider_run = session.scalar(select(LiveRun).where(LiveRun.run_id == "failed-provider"))

    assert provider_run is not None
    assert recommendation is not None
    assert recommendation.grade == "reject"
    assert "provider_health_warning" in json.loads(recommendation.risk_flags_json)


def test_recommendation_service_uses_active_threshold_policy(tmp_path) -> None:
    engine = create_engine_from_url(f"sqlite:///{(tmp_path / 'policy-recs.sqlite').as_posix()}")
    Base.metadata.create_all(engine)
    _seed_candidate(engine, edge=0.08, confidence=0.8)
    _seed_active_threshold_policy(engine, min_edge=0.1, min_confidence=0.5)

    RecommendationService(engine, _settings()).generate(stale_after_minutes=100000)

    with session_scope(engine) as session:
        recommendation = session.scalar(select(PaperRecommendation))

    assert recommendation is not None
    assert recommendation.grade == "reject"
    assert "edge_below_threshold" in json.loads(recommendation.risk_flags_json)
    assert "active threshold policy" in recommendation.rationale


def _seed_candidate(
    engine,
    *,
    edge: float,
    confidence: float,
    odds_decimal: float = 2.0,
    snapshot_time: str = "2026-05-19T12:00:00+00:00",
    model_probability: float | None = None,
    prediction_bookmaker_probability: float | None = None,
) -> None:
    with session_scope(engine) as session:
        match = MatchRepository(session).add(
            source="misli_public",
            source_match_id="misli:football:2816300",
            league="Sample Premier",
            home_team="Forest City",
            away_team="Eastport Athletic",
            kickoff_time="2026-05-19T20:30:00+04:00",
        )
        OddsSnapshotRepository(session).add(
            match_id=match.id,
            source="misli_public",
            bookmaker="Misli.az",
            market="1X2",
            selection="HOME",
            odds_decimal=odds_decimal,
            implied_probability=1 / odds_decimal,
            snapshot_time=snapshot_time,
        )
        PredictionRepository(session).add(
            match_id=match.id,
            market="1X2",
            selection="HOME",
            model_name="baseline_heuristic",
            model_version="v0",
            model_probability=model_probability
            if model_probability is not None
            else (1 / odds_decimal) + edge,
            bookmaker_probability=prediction_bookmaker_probability
            if prediction_bookmaker_probability is not None
            else 1 / odds_decimal,
            edge=edge,
            confidence_score=confidence,
            decision="PENDING",
            reason="seed prediction",
        )


def _seed_active_threshold_policy(
    engine,
    *,
    min_edge: float,
    min_confidence: float,
) -> None:
    with session_scope(engine) as session:
        session.add(
            ThresholdPolicyRun(
                state="applied",
                decision="tighten",
                active=True,
                source_backtest_id=None,
                source_backtest_name="pytest_policy",
                sample_size=350,
                roi=-0.1,
                hit_rate=0.4,
                brier_score=0.3,
                log_loss=0.8,
                max_drawdown_units=-15.0,
                policy_values_json=json.dumps(
                    {
                        "min_edge": min_edge,
                        "min_expected_value": 0.0,
                        "min_odds": 1.7,
                        "max_odds": 3.5,
                        "min_confidence": min_confidence,
                        "recommendations_enabled": True,
                        "combinations_enabled": False,
                    }
                ),
                rollback_policy_values_json=json.dumps({"min_edge": 0.07}),
                evidence_json=json.dumps({"sample_size": 350}),
                rationale="Apply stricter test policy.",
                risk_flags_json=json.dumps(["negative_singles_roi"]),
            )
        )


def _seed_new_prediction(
    engine,
    *,
    edge: float,
    confidence: float,
    model_probability: float,
    prediction_bookmaker_probability: float = 0.5,
) -> None:
    with session_scope(engine) as session:
        match = MatchRepository(session).get_by_source_id(
            source="misli_public",
            source_match_id="misli:football:2816300",
        )
        assert match is not None
        PredictionRepository(session).add(
            match_id=match.id,
            market="1X2",
            selection="HOME",
            model_name="baseline_heuristic",
            model_version="v0",
            model_probability=model_probability,
            bookmaker_probability=prediction_bookmaker_probability,
            edge=edge,
            confidence_score=confidence,
            decision="PENDING",
            reason="replacement seed prediction",
        )


def _settings() -> Settings:
    return Settings(
        database_url="sqlite:///:memory:",
        default_sport="football",
        default_market="1X2",
        default_stake_units=1.0,
        min_edge=0.07,
        min_odds=1.7,
        max_odds=3.5,
        feature_version="v0_baseline",
        model_name="baseline_heuristic",
        model_version="v0",
        elo_initial_rating=1500,
        elo_k_factor=20,
        elo_home_advantage=65,
        log_level="INFO",
        live_collection_enabled=True,
    )
